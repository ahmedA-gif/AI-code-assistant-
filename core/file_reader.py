import os
import re
from pathlib import Path

class FileReader:    
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root)
    
    def read_file(self, file_path):
        """Return file content as string."""
        p = Path(file_path)
        return p.read_text(encoding='utf-8', errors='ignore')
    
    def analyze_file(self, file_path, content):
        analysis = {
            'functions': [],
            'classes': [],
            'todos': [],
            'deprecated': []
        }
        lines = content.split('\n')
        
        # Regex patterns
        func_pattern = re.compile(r'^\s*def\s+(\w+)\s*\(')
        class_pattern = re.compile(r'^\s*class\s+(\w+)\s*[:\(]')
        todo_pattern = re.compile(r'(TODO|FIXME|BUG):?\s*(.*)', re.IGNORECASE)
        deprecated_pattern = re.compile(r'@deprecated|\bdeprecated\b', re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            func_match = func_pattern.match(line)
            if func_match:
                analysis['functions'].append({
                    'name': func_match.group(1),
                    'line': i,
                    'content': line.strip()
                })
            class_match = class_pattern.match(line)
            if class_match:
                analysis['classes'].append({
                    'name': class_match.group(1),
                    'line': i,
                    'content': line.strip()
                })
            todo_match = todo_pattern.search(line)
            if todo_match:
                analysis['todos'].append({
                    'type': todo_match.group(1).upper(),
                    'message': todo_match.group(2).strip(),
                    'line': i
                })
            if deprecated_pattern.search(line):
                analysis['deprecated'].append({'line': i, 'content': line.strip()})
        
        return analysis