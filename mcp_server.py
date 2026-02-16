import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from core.code_search import CodeSearch
from core.context_manager import ContextManager
from core.git_integration import GitIntegration
from core.llm_interface import LLMInterface
from core.test_runner import TestRunner
from core.static_analysis import StaticAnalyzer
from config import Config

# Initialize MCP server
mcp = FastMCP("GrokCodeAssistant")

# Initialize core modules (using default workspace from config)
workspace_root = Config.WORKSPACE_ROOT
code_search = CodeSearch(workspace_root=workspace_root)
context_manager = ContextManager(workspace_root=workspace_root)
git_integration = GitIntegration(workspace_root=workspace_root)
llm_interface = LLMInterface(config=Config)
test_runner = TestRunner(workspace_root=workspace_root)
static_analyzer = StaticAnalyzer(workspace_root=workspace_root)

@mcp.tool()
def search_keyword(keyword: str, file_pattern: str = "*") -> list:
    """Search for a keyword in the codebase using regex."""
    return code_search.keyword_search(keyword, file_pattern)

@mcp.tool()
def search_semantic(query: str, top_k: int = 5) -> dict:
    """Perform semantic search using LlamaIndex."""
    return code_search.semantic_search(query, top_k)

@mcp.tool()
def get_project_summary() -> str:
    """Get a summary of the project structure and dependencies."""
    return context_manager.get_summary()

@mcp.tool()
def git_status() -> dict:
    """Get current git status."""
    return git_integration.get_status()

@mcp.tool()
def git_commit(message: str) -> dict:
    """Commit all changes with a message."""
    return git_integration.commit(message)

@mcp.tool()
def suggest_code_improvements(code: str, context: str = "") -> str:
    """Get AI suggestions for code improvement."""
    return llm_interface.get_suggestion('refactor', code, context)

@mcp.tool()
def explain_code(code: str) -> str:
    """Get an explanation of what the code does."""
    return llm_interface.get_suggestion('explain', code)

@mcp.tool()
def find_bugs(code: str) -> str:
    """Identify potential bugs or security issues."""
    return llm_interface.get_suggestion('bugfix', code)

@mcp.tool()
def run_tests(test_path: str = "", framework: str = "pytest") -> dict:
    """Run tests in the specified path."""
    full_path = os.path.join(workspace_root, test_path) if test_path else workspace_root
    return test_runner.run_tests(full_path, framework)

@mcp.tool()
def analyze_code(path: str, tool: str = "flake8") -> dict:
    """Run static analysis on a file or directory."""
    full_path = os.path.join(workspace_root, path)
    return static_analyzer.analyze(full_path, tool)

if __name__ == "__main__":
    mcp.run()