import os
import ast
from pathlib import Path
from collections import defaultdict

class ContextManager:
    
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root).resolve()
        self.cache = None
    
    def get_project_context(self, refresh=False):
        if self.cache and not refresh:
            return self.cache
            
        context = {
            "files": [],
            "folders": [],
            "imports": defaultdict(list)
        }
        
        # Crawl through the project
        for root, dirs, files in os.walk(self.workspace_root):
            # Skip hidden folders like .git or .mcp_cache
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            rel_root = Path(root).relative_to(self.workspace_root)
            if str(rel_root) != ".":
                context["folders"].append(str(rel_root))
                
            for f in files:
                if f.endswith('.py'):
                    rel_path = str(rel_root / f) if str(rel_root) != "." else f
                    context["files"].append(rel_path)
                    
                    # Look inside the file for imports
                    file_imports = self._extract_imports(Path(root) / f)
                    if file_imports:
                        context["imports"][rel_path] = file_imports
        
        self.cache = context
        return context

    def _extract_imports(self, file_path):
        found_imports = []
        try:
            code = file_path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Handles 'import os'
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        found_imports.append(alias.name)
                # Handles 'from os import path'
                elif isinstance(node, ast.ImportFrom):
                    module = node.module if node.module else ""
                    for alias in node.names:
                        found_imports.append(module + "." + alias.name)
        except Exception:
            # If the code has a syntax error, we just skip it
            pass
        return found_imports

    def get_summary(self):
        ctx = self.get_project_context()
        summary = "PROJECT STRUCTURE:\n"
        summary += "- Files: " + ", ".join(ctx['files']) + "\n"
        summary += "- Key Imports: "
        
        # Flatten imports to see what the project depends on most
        all_deps = []
        for deps in ctx['imports'].values():
            all_deps.extend(deps)
        
        unique_deps = sorted(list(set(all_deps)))[:15] # Top 15 unique imports
        summary += ", ".join(unique_deps)
        return summary