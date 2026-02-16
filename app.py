import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
from models import db, User
from core.code_search import CodeSearch, search_keyword
from core.file_reader import FileReader
from core.test_runner import TestRunner
from core.static_analysis import StaticAnalyzer
from core.context_manager import ContextManager
from core.git_integration import GitIntegration
from core.llm_interface import LLMInterface
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Database
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

os.makedirs(app.config['WORKSPACE_ROOT'], exist_ok=True)

# Initialize core modules
code_search_engine = CodeSearch(workspace_root=app.config['WORKSPACE_ROOT'])
file_reader = FileReader(workspace_root=app.config['WORKSPACE_ROOT'])
test_runner = TestRunner(workspace_root=app.config['WORKSPACE_ROOT'])
static_analyzer = StaticAnalyzer(workspace_root=app.config['WORKSPACE_ROOT'])
context_manager = ContextManager(workspace_root=app.config['WORKSPACE_ROOT'])
git_integration = GitIntegration(workspace_root=app.config['WORKSPACE_ROOT'])
llm_interface = LLMInterface(config=app.config)

# Create tables
with app.app_context():
    db.create_all()

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    logging.error(f"Unhandled Exception: {str(e)}", exc_info=True)
    return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

# ===== AUTH ROUTES =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ===== PROTECTED MAIN PAGE =====
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

# ===== API ROUTES (all require login) =====
@app.route('/api/files', methods=['GET'])
@login_required
def list_files():
    path = request.args.get('path', '')
    full_path = os.path.join(app.config['WORKSPACE_ROOT'], path)
    if not os.path.realpath(full_path).startswith(os.path.realpath(app.config['WORKSPACE_ROOT'])):
        return jsonify({'error': 'Access denied'}), 403
    try:
        entries = []
        for entry in os.listdir(full_path):
            entry_path = os.path.join(full_path, entry)
            entries.append({
                'name': entry,
                'type': 'directory' if os.path.isdir(entry_path) else 'file',
                'size': os.path.getsize(entry_path) if os.path.isfile(entry_path) else None,
                'modified': os.path.getmtime(entry_path)
            })
        return jsonify({'path': path, 'entries': entries})
    except FileNotFoundError:
        return jsonify({'error': 'Path not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/read_file', methods=['GET'])
@login_required
def read_file():
    file_path = request.args.get('path', '')
    full_path = os.path.join(app.config['WORKSPACE_ROOT'], file_path)
    if not os.path.realpath(full_path).startswith(os.path.realpath(app.config['WORKSPACE_ROOT'])):
        return jsonify({'error': 'Access denied'}), 403
    try:
        content = file_reader.read_file(full_path)
        analysis = file_reader.analyze_file(full_path, content)
        return jsonify({
            'path': file_path,
            'content': content,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
@login_required
def search():
    data = request.get_json()
    keyword = data.get('keyword', '')
    file_pattern = data.get('file_pattern', '*')
    old_cwd = os.getcwd()
    try:
        os.chdir(app.config['WORKSPACE_ROOT'])
        results = search_keyword(keyword, file_pattern, context_lines=2)
    except Exception as e:
        logging.error(f"Search error: {e}")
        results = []
    finally:
        os.chdir(old_cwd)
    return jsonify({'results': results})

@app.route('/api/search_semantic', methods=['POST'])
@login_required
def search_semantic():
    data = request.get_json()
    query = data.get('query', '')
    idx = code_search_engine.get_index()
    if idx is None:
        return jsonify({'error': 'Semantic search not available (missing embeddings or index)'}), 503
    try:
        query_engine = idx.as_query_engine(similarity_top_k=5)
        response = query_engine.query(query)
        return jsonify({'response': str(response)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run_tests', methods=['POST'])
@login_required
def run_tests():
    data = request.get_json()
    test_path = data.get('test_path', '')
    framework = data.get('framework', 'pytest')
    full_path = os.path.join(app.config['WORKSPACE_ROOT'], test_path) if test_path else app.config['WORKSPACE_ROOT']
    if test_path and not os.path.realpath(full_path).startswith(os.path.realpath(app.config['WORKSPACE_ROOT'])):
        return jsonify({'error': 'Access denied'}), 403
    try:
        result = test_runner.run_tests(path=full_path, framework=framework)
        logging.info(f"Test result: {result}")
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        flat_result = {
            'framework': result['framework'],
            'status': result['status'],
            'total': result['counts']['total'],
            'passed': result['counts']['passed'],
            'failed': result['counts']['failed'],
            'errors': result['counts']['errors'],
            'skipped': result['counts']['skipped'],
            'output': result['output_snippet'],
            'full_logs': result['full_logs']
        }
        if flat_result['failed'] > 0 or flat_result['errors'] > 0:
            suggestion = llm_interface.suggest_test_fixes(flat_result['full_logs'])
            flat_result['suggestion'] = suggestion
        return jsonify(flat_result)
    except Exception as e:
        logging.error(f"Test endpoint exception: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze():
    data = request.get_json()
    target_path = data.get('path', '')
    tool = data.get('tool', 'pylint')
    full_path = os.path.join(app.config['WORKSPACE_ROOT'], target_path)
    if not os.path.realpath(full_path).startswith(os.path.realpath(app.config['WORKSPACE_ROOT'])):
        return jsonify({'error': 'Access denied'}), 403
    try:
        results = static_analyzer.analyze(path=full_path, tool=tool)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suggest', methods=['POST'])
@login_required
def suggest():
    data = request.get_json()
    prompt_type = data.get('type', 'refactor')
    code_context = data.get('code', '')
    additional_context = data.get('context', '')
    try:
        suggestion = llm_interface.get_suggestion(
            prompt_type=prompt_type,
            code=code_context,
            context=additional_context
        )
        return jsonify({'suggestion': suggestion})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['GET'])
@login_required
def get_context():
    try:
        context = context_manager.get_project_context()
        context['imports'] = dict(context['imports'])
        return jsonify(context)
    except Exception as e:
        logging.error(f"Context error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/status', methods=['GET'])
@login_required
def git_status():
    try:
        status = git_integration.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/commit', methods=['POST'])
@login_required
def git_commit():
    data = request.get_json()
    message = data.get('message', '')
    try:
        result = git_integration.quick_save(message)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    target_dir = request.form.get('target_dir', '')
    upload_path = os.path.join(app.config['WORKSPACE_ROOT'], target_dir)
    os.makedirs(upload_path, exist_ok=True)

    uploaded = []
    errors = []

    for file in files:
        if file.filename == '':
            continue
        filename = secure_filename(file.filename)
        if not filename:
            errors.append(f"Invalid filename: {file.filename}")
            continue
        save_path = os.path.join(upload_path, filename)
        try:
            file.save(save_path)
            uploaded.append(filename)
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    return jsonify({
        'uploaded': uploaded,
        'errors': errors,
        'message': f'Uploaded {len(uploaded)} file(s), {len(errors)} error(s).'
    })

# ===== CHAT ENDPOINT =====
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    current_file = data.get('current_file', '')
    file_content = data.get('file_content', '')

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # Build context
    context = f"Current file: {current_file}\n" if current_file else ""
    if file_content:
        context += f"File content:\n```\n{file_content[:2000]}```\n"  # limit length

    system_prompt = """You are an AI coding assistant integrated into a development environment. 
You have access to the current file and the project workspace. Answer questions, help with code, 
explain concepts, and assist with debugging. Be concise but thorough."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{context}\nUser question: {user_message}"}
    ]

    try:
        response = llm_interface._call_llm(messages, temperature=0.3)
        return jsonify({'response': response})
    except Exception as e:
        logging.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)