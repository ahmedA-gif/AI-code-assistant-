import os
from pathlib import Path

# Note: Requires 'pip install GitPython'
import git

class GitIntegration:
    
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root).resolve()
        try:
            self.repo = git.Repo(self.workspace_root)
        except Exception:
            self.repo = None
    
    def get_status(self):
        if not self.repo:
            return {"error": "This directory is not a Git repository."}
            
        try:
            status = {
                "branch": self.repo.active_branch.name,
                "modified": [item.a_path for item in self.repo.index.diff(None)],
                "staged": [item.a_path for item in self.repo.index.diff("HEAD")],
                "untracked": self.repo.untracked_files,
                "recent_commits": []
            }
            
            for commit in self.repo.iter_commits(max_count=3):
                status["recent_commits"].append(commit.message.strip())
                
            return status
        except Exception as e:
            return {"error": "Could not fetch git status: " + str(e)}

    def quick_save(self, message):
        if not self.repo:
            return {"error": "Cannot save: Not a git repository."}
            
        try:
            # Stage all changes (git add .)
            self.repo.git.add(A=True)
            
            # Commit (git commit -m "...")
            new_commit = self.repo.index.commit(message)
            
            return {
                "success": True, 
                "message": "Changes saved successfully",
                "hash": new_commit.hexsha[:7]
            }
        except Exception as e:
            return {"error": "Failed to commit: " + str(e)}

    def get_summary_for_ai(self):
        status = self.get_status()
        if "error" in status:
            return status["error"]
            
        summary = "GIT STATE:\n"
        summary += "- Branch: " + status['branch'] + "\n"
        summary += "- Pending Changes: " + str(len(status['modified']) + len(status['untracked'])) + " files\n"
        if status['recent_commits']:
            summary += "- Last Commit: " + status['recent_commits'][0]
            
        return summary