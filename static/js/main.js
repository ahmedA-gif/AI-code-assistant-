// ==========================
// Modern Frontend for Code Assistant MCP
// ==========================

let editor;
let currentFilePath = '';
let previewVisible = false;

// Modal state
let modalResolve = null;
let modalReject = null;

// Initialize Monaco Editor
require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('editor-container'), {
        value: '// Select a file to edit\n',
        language: 'plaintext',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        minimap: { enabled: false }
    });
    loadFileTree('');
});

// ===== MESSAGE HANDLING =====
const messagesContainer = document.getElementById('messages');

function addMessage(content, type = 'system', isAI = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    if (isAI) msgDiv.classList.add('ai');

    const iconSpan = document.createElement('span');
    iconSpan.className = 'msg-icon';
    let iconHtml = '';
    switch (type) {
        case 'success': iconHtml = '<i class="fas fa-check-circle"></i>'; break;
        case 'error': iconHtml = '<i class="fas fa-exclamation-circle"></i>'; break;
        case 'warning': iconHtml = '<i class="fas fa-exclamation-triangle"></i>'; break;
        default: iconHtml = '<i class="fas fa-info-circle"></i>';
    }
    iconSpan.innerHTML = iconHtml;

    const contentSpan = document.createElement('span');
    contentSpan.className = 'msg-content';
    contentSpan.textContent = content;

    const timeSpan = document.createElement('span');
    timeSpan.className = 'msg-time';
    timeSpan.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    msgDiv.appendChild(iconSpan);
    msgDiv.appendChild(contentSpan);
    msgDiv.appendChild(timeSpan);

    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Clear messages
document.getElementById('clear-messages').addEventListener('click', () => {
    messagesContainer.innerHTML = '';
    addMessage('Welcome to Code Assistant MCP. Select a file or run an action.', 'system');
});

// ===== MODAL =====
const modalOverlay = document.getElementById('modal-overlay');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const modalInput = document.getElementById('modal-input');
const modalConfirm = document.getElementById('modal-confirm');
const modalCancel = document.getElementById('modal-cancel');
const modalClose = document.getElementById('modal-close');

function showModal(title, message, defaultValue = '') {
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    modalInput.value = defaultValue;
    modalOverlay.classList.add('show');
    modalInput.focus();

    return new Promise((resolve, reject) => {
        modalResolve = resolve;
        modalReject = reject;
    });
}

function closeModal() {
    modalOverlay.classList.remove('show');
    modalResolve = null;
    modalReject = null;
}

modalConfirm.addEventListener('click', () => {
    if (modalResolve) {
        modalResolve(modalInput.value);
    }
    closeModal();
});

modalCancel.addEventListener('click', () => {
    if (modalReject) {
        modalReject('Cancelled');
    }
    closeModal();
});

modalClose.addEventListener('click', () => {
    if (modalReject) {
        modalReject('Closed');
    }
    closeModal();
});

modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) {
        if (modalReject) {
            modalReject('Closed');
        }
        closeModal();
    }
});

// ===== FILE TREE =====
const fileTreeDiv = document.getElementById('file-tree');
const refreshBtn = document.getElementById('refresh-files');

function loadFileTree(path) {
    fileTreeDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-pulse"></i> Loading...</div>';
    fetch(`/api/files?path=${encodeURIComponent(path)}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                addMessage('Error loading files: ' + data.error, 'error');
                fileTreeDiv.innerHTML = '';
                return;
            }
            renderFileTree(data.entries, path);
        })
        .catch(err => {
            addMessage('Network error loading files: ' + err, 'error');
            fileTreeDiv.innerHTML = '';
        });
}

function renderFileTree(entries, currentPath) {
    fileTreeDiv.innerHTML = '';

    // Parent directory
    if (currentPath) {
        const parentDiv = document.createElement('div');
        parentDiv.className = 'dir up';
        parentDiv.innerHTML = '📁 <a href="#" onclick="loadFileTree(\'' + getParentPath(currentPath) + '\')">..</a>';
        fileTreeDiv.appendChild(parentDiv);
    }

    const ul = document.createElement('ul');
    entries.sort((a, b) => {
        if (a.type === 'directory' && b.type !== 'directory') return -1;
        if (a.type !== 'directory' && b.type === 'directory') return 1;
        return a.name.localeCompare(b.name);
    }).forEach(entry => {
        const li = document.createElement('li');
        li.className = entry.type === 'directory' ? 'dir' : 'file';
        li.textContent = entry.name;

        const fullPath = currentPath ? currentPath + '/' + entry.name : entry.name;
        if (entry.type === 'file') {
            li.dataset.path = fullPath;
        }

        li.onclick = (e) => {
            e.stopPropagation();
            if (entry.type === 'directory') {
                const childUl = li.querySelector('ul');
                if (childUl) {
                    childUl.classList.toggle('collapsed');
                } else {
                    loadFileTree(fullPath);
                }
            } else {
                openFile(fullPath);
            }
        };
        ul.appendChild(li);
    });
    fileTreeDiv.appendChild(ul);
}

function getParentPath(path) {
    const parts = path.split('/');
    parts.pop();
    return parts.join('/');
}

refreshBtn.addEventListener('click', () => loadFileTree(currentFilePath ? currentFilePath.split('/').slice(0, -1).join('/') : ''));

// ===== OPEN FILE =====
function openFile(relativePath) {
    currentFilePath = relativePath;
    addMessage(`Opening file: ${relativePath}`, 'system');
    document.getElementById('file-status').textContent = relativePath;
    fetch(`/api/read_file?path=${encodeURIComponent(relativePath)}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                addMessage('Error reading file: ' + data.error, 'error');
                return;
            }
            editor.setValue(data.content);
            const ext = relativePath.split('.').pop();
            const langMap = {
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'html': 'html',
                'css': 'css',
                'json': 'json',
                'md': 'markdown'
            };
            monaco.editor.setModelLanguage(editor.getModel(), langMap[ext] || 'plaintext');

            let info = `**${relativePath}** — `;
            info += `${data.analysis.functions.length} function(s), ${data.analysis.classes.length} class(es)`;
            if (data.analysis.todos.length) {
                info += `, ${data.analysis.todos.length} TODO(s)`;
            }
            addMessage(info, 'success');

            // Update preview if visible
            if (previewVisible) {
                updatePreview(data.content);
            }
        })
        .catch(err => addMessage('Error: ' + err, 'error'));
}

// ===== PREVIEW PANEL =====
const previewPanel = document.getElementById('preview-panel');
const previewContent = document.getElementById('preview-content');
const togglePreviewBtn = document.getElementById('toggle-preview');
const closePreviewBtn = document.getElementById('close-preview');

function updatePreview(content) {
    previewContent.textContent = content;
}

togglePreviewBtn.addEventListener('click', () => {
    if (!previewVisible) {
        previewPanel.style.display = 'flex';
        previewVisible = true;
        if (currentFilePath) {
            updatePreview(editor.getValue());
        }
    } else {
        previewPanel.style.display = 'none';
        previewVisible = false;
    }
});

closePreviewBtn.addEventListener('click', () => {
    previewPanel.style.display = 'none';
    previewVisible = false;
});

// Initially hide preview
previewPanel.style.display = 'none';

// ===== BUTTON ACTIONS (using modal instead of prompt) =====
document.getElementById('btn-files').addEventListener('click', () => loadFileTree(''));

document.getElementById('btn-search').addEventListener('click', async () => {
    try {
        const keyword = await showModal('Search Code', 'Enter keyword to search:');
        if (!keyword) {
            addMessage('Search cancelled.', 'warning');
            return;
        }

        addMessage(`Searching for "${keyword}"...`, 'system');
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword })
        });
        const data = await res.json();
        if (data.error) {
            addMessage('Search error: ' + data.error, 'error');
            return;
        }
        if (data.results.length === 0) {
            addMessage(`No results for "${keyword}"`, 'warning');
            return;
        }
        let summary = `Found ${data.results.length} result(s) for "${keyword}":\n`;
        data.results.slice(0, 5).forEach(r => {
            summary += `\n📄 ${r.file}:${r.line} — ${r.content}`;
        });
        if (data.results.length > 5) summary += `\n... and ${data.results.length - 5} more.`;
        addMessage(summary, 'success');
    } catch (err) {
        addMessage('Search cancelled.', 'warning');
    }
});

document.getElementById('btn-tests').addEventListener('click', async () => {
    try {
        const testPath = await showModal('Run Tests', 'Enter relative path to test (or leave empty for all):');
        addMessage(`Running tests...`, 'system');
        const res = await fetch('/api/run_tests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_path: testPath || '' })
        });
        const data = await res.json();
        if (data.error) {
            addMessage('Test error: ' + data.error, 'error');
            return;
        }
        const total = data.total || 0;
        const passed = data.passed || 0;
        const failed = data.failed || 0;
        const errors = data.errors || 0;
        const skipped = data.skipped || 0;

        let msg = `Tests (${data.framework}): Total ${total}, ✅ Passed ${passed}, ❌ Failed ${failed}, ⚠️ Errors ${errors}, Skipped ${skipped}`;
        if (failed > 0 || errors > 0) {
            msg += '\n\n' + (data.output || '');
        }
        addMessage(msg, failed > 0 ? 'error' : 'success');

        if (data.suggestion) {
            const aiMsg = document.createElement('div');
            aiMsg.className = 'message ai typing';
            aiMsg.innerHTML = `<span class="msg-icon"><i class="fas fa-robot"></i></span><span class="msg-content">${data.suggestion}</span><span class="msg-time">${new Date().toLocaleTimeString()}</span>`;
            messagesContainer.appendChild(aiMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            setTimeout(() => aiMsg.classList.remove('typing'), 1000);
        }
    } catch (err) {
        addMessage('Test cancelled.', 'warning');
    }
});

document.getElementById('btn-analyze').addEventListener('click', async () => {
    try {
        const targetPath = await showModal('Static Analysis', 'Enter file or directory to analyze (relative):');
        if (!targetPath) {
            addMessage('Analysis cancelled.', 'warning');
            return;
        }

        addMessage(`Analyzing ${targetPath}...`, 'system');
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: targetPath, tool: 'pylint' })
        });
        const data = await res.json();
        if (data.error) {
            addMessage('Analysis error: ' + data.error, 'error');
            return;
        }
        const issues = data.issues || [];
        if (issues.length === 0) {
            addMessage(`No issues found in ${targetPath}`, 'success');
        } else {
            let msg = `Found ${issues.length} issue(s) with ${data.tool}:\n`;
            issues.slice(0, 10).forEach(issue => {
                msg += `\n- Line ${issue.line || issue.location}: ${issue.message}`;
            });
            if (issues.length > 10) msg += `\n... and ${issues.length - 10} more.`;
            addMessage(msg, 'warning');
        }
    } catch (err) {
        addMessage('Analysis cancelled.', 'warning');
    }
});

document.getElementById('btn-context').addEventListener('click', () => {
    addMessage(`Fetching project context...`, 'system');
    fetch('/api/context')
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                addMessage('Context error: ' + data.error, 'error');
                return;
            }
            const files = data.files || [];
            const folders = data.folders || [];
            let msg = `📁 Project Context\n`;
            msg += `- Root: ${data.root || 'workspace'}\n`;
            msg += `- Folders: ${folders.length}\n`;
            msg += `- Files: ${files.length} (showing first 10)\n`;
            msg += files.slice(0, 10).map(f => `  • ${f}`).join('\n');
            if (files.length > 10) msg += `\n  ... and ${files.length - 10} more.`;
            addMessage(msg, 'success');
        });
});

document.getElementById('btn-git').addEventListener('click', () => {
    addMessage(`Fetching git status...`, 'system');
    fetch('/api/git/status')
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                addMessage('Git error: ' + data.error, 'error');
                return;
            }
            let msg = `🌿 Git Status (branch: ${data.branch})\n`;
            if (data.modified?.length) msg += `\n📝 Modified (${data.modified.length}):\n  ` + data.modified.slice(0, 5).join('\n  ') + (data.modified.length > 5 ? '\n  ...' : '');
            if (data.staged?.length) msg += `\n\n✅ Staged (${data.staged.length}):\n  ` + data.staged.slice(0, 5).join('\n  ') + (data.staged.length > 5 ? '\n  ...' : '');
            if (data.untracked?.length) msg += `\n\n❓ Untracked (${data.untracked.length}):\n  ` + data.untracked.slice(0, 5).join('\n  ') + (data.untracked.length > 5 ? '\n  ...' : '');
            if (data.ahead || data.behind) msg += `\n\n↑ Ahead ${data.ahead} · ↓ Behind ${data.behind}`;
            addMessage(msg, 'success');
        });
});

document.getElementById('btn-ai').addEventListener('click', async () => {
    const code = editor.getValue();
    if (!code.trim()) {
        addMessage('Editor is empty. Write some code or open a file first.', 'warning');
        return;
    }

    try {
        const type = await showModal('AI Suggestion', 'Enter suggestion type (refactor, explain, generate, bugfix):', 'refactor');
        if (!type) {
            addMessage('AI suggestion cancelled.', 'warning');
            return;
        }

        addMessage(`🤖 Asking AI for ${type} suggestion...`, 'system');
        const res = await fetch('/api/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, code })
        });
        const data = await res.json();
        if (data.error) {
            addMessage('AI error: ' + data.error, 'error');
            return;
        }
        const aiMsg = document.createElement('div');
        aiMsg.className = 'message ai typing';
        aiMsg.innerHTML = `<span class="msg-icon"><i class="fas fa-robot"></i></span><span class="msg-content">${data.suggestion}</span><span class="msg-time">${new Date().toLocaleTimeString()}</span>`;
        messagesContainer.appendChild(aiMsg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        setTimeout(() => aiMsg.classList.remove('typing'), 800);
    } catch (err) {
        addMessage('AI suggestion cancelled.', 'warning');
    }
});

// ===== UPLOAD FILE =====
document.getElementById('upload-file').addEventListener('click', () => {
    document.getElementById('file-upload-input').click();
});

document.getElementById('file-upload-input').addEventListener('change', async (e) => {
    const files = e.target.files;
    if (files.length === 0) return;

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    const targetDir = currentFilePath ? currentFilePath.split('/').slice(0, -1).join('/') : '';
    formData.append('target_dir', targetDir);

    addMessage(`Uploading ${files.length} file(s)...`, 'system');

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (res.ok) {
            addMessage(`✅ Uploaded ${data.uploaded.length} file(s) successfully.`, 'success');
            if (data.errors.length) {
                addMessage(`Errors: ${data.errors.join(', ')}`, 'warning');
            }
            loadFileTree(targetDir);
        } else {
            addMessage(`Upload error: ${data.error}`, 'error');
        }
    } catch (err) {
        addMessage(`Network error: ${err}`, 'error');
    }

    e.target.value = '';
});

// ===== FILE PREVIEW ON HOVER =====
const hoverPreviewDiv = document.getElementById('file-preview');
const hoverPreviewContent = document.getElementById('hover-preview-content');
let previewTimer = null;
let currentHoverItem = null;

function hideHoverPreview() {
    if (previewTimer) {
        clearTimeout(previewTimer);
        previewTimer = null;
    }
    hoverPreviewDiv.style.display = 'none';
}

function showHoverPreview(event, filePath) {
    if (previewTimer) clearTimeout(previewTimer);
    
    previewTimer = setTimeout(async () => {
        try {
            const res = await fetch(`/api/read_file?path=${encodeURIComponent(filePath)}`);
            const data = await res.json();
            if (data.error) {
                console.warn('Preview error:', data.error);
                return;
            }
            
            const lines = data.content.split('\n').slice(0, 15);
            let previewText = lines.join('\n');
            if (data.content.split('\n').length > 15) previewText += '\n... (truncated)';
            
            hoverPreviewContent.textContent = previewText;
            
            const x = event.clientX + 20;
            const y = event.clientY + 10;
            hoverPreviewDiv.style.left = x + 'px';
            hoverPreviewDiv.style.top = y + 'px';
            hoverPreviewDiv.style.display = 'block';
        } catch (err) {
            console.error('Preview fetch error:', err);
        } finally {
            previewTimer = null;
        }
    }, 500);
}

fileTreeDiv.addEventListener('mouseover', (e) => {
    const li = e.target.closest('li.file');
    if (!li) {
        hideHoverPreview();
        return;
    }
    
    const filePath = li.dataset.path;
    if (!filePath) return;
    
    if (currentHoverItem !== li) {
        hideHoverPreview();
        currentHoverItem = li;
        showHoverPreview(e, filePath);
    }
});

fileTreeDiv.addEventListener('mouseout', (e) => {
    const related = e.relatedTarget;
    if (!fileTreeDiv.contains(related)) {
        hideHoverPreview();
        currentHoverItem = null;
    }
});

// ===== USER DROPDOWN =====
const userMenuBtn = document.getElementById('user-menu-btn');
const userDropdown = document.getElementById('user-dropdown');

if (userMenuBtn) {
    userMenuBtn.addEventListener('click', () => {
        userDropdown.classList.toggle('show');
    });

    window.addEventListener('click', (e) => {
        if (!userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) {
            userDropdown.classList.remove('show');
        }
    });
}

// ===== CHAT =====
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');

function escapeHTML(str) {
    return str.replace(/[&<>"]/g, function(match) {
        if (match === '&') return '&amp;';
        if (match === '<') return '&lt;';
        if (match === '>') return '&gt;';
        if (match === '"') return '&quot;';
        return match;
    });
}

function addUserMessage(content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system';
    msgDiv.innerHTML = `
        <span class="msg-icon"><i class="fas fa-user"></i></span>
        <span class="msg-content">${escapeHTML(content)}</span>
        <span class="msg-time">${new Date().toLocaleTimeString()}</span>
    `;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addAIMessage(content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    msgDiv.innerHTML = `
        <span class="msg-icon"><i class="fas fa-robot"></i></span>
        <span class="msg-content">${escapeHTML(content)}</span>
        <span class="msg-time">${new Date().toLocaleTimeString()}</span>
    `;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addUserMessage(message);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Show typing indicator
    const typingMsg = document.createElement('div');
    typingMsg.className = 'message ai typing';
    typingMsg.innerHTML = `<span class="msg-icon"><i class="fas fa-robot"></i></span><span class="msg-content">...</span><span class="msg-time">${new Date().toLocaleTimeString()}</span>`;
    messagesContainer.appendChild(typingMsg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                current_file: currentFilePath,
                file_content: editor.getValue()
            })
        });
        const data = await response.json();
        typingMsg.remove();
        if (data.error) {
            addAIMessage('Error: ' + data.error);
        } else {
            addAIMessage(data.response);
        }
    } catch (err) {
        typingMsg.remove();
        addAIMessage('Network error: ' + err);
    }
}

chatSend.addEventListener('click', sendChatMessage);

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
});

chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});