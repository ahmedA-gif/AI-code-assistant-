import subprocess
import os
from pathlib import Path

class StaticAnalyzer:
    
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root).resolve()
    
    def analyze(self, path, tool='flake8'):
       
        target_path = Path(path).resolve()
        if not target_path.exists():
            return {"error": "Path " + str(path) + " not found."}

        
        cmds = {
            'flake8': ['flake8', str(target_path)],
            'pylint': ['pylint', str(target_path), '--output-format=text'],
            'mypy': ['mypy', str(target_path), '--ignore-missing-imports']
        }

        if tool not in cmds:
            return {"error": "Tool " + tool + " is not supported."}

        try:
            # Run the tool
            proc = subprocess.run(
                cmds[tool], 
                capture_output=True, 
                text=True, 
                timeout=30 
            )
            
            raw_output = proc.stdout + proc.stderr
            issues = []
            
            for line in raw_output.splitlines():
                if ":" in line:
                    parts = line.split(":", 3)
                    if len(parts) >= 3:
                        issues.append({
                            "location": "Line " + parts[1].strip(),
                            "message": parts[-1].strip()
                        })

            return {
                "tool": tool,
                "target": str(target_path.relative_to(self.workspace_root)),
                "issue_count": len(issues),
                "issues": issues[:20], 
                "summary": "Found " + str(len(issues)) + " issues using " + tool
            }

        except Exception as e:
            return {"error": "Analysis failed: " + str(e)}