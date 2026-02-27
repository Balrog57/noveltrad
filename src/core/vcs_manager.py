import os
import subprocess
from typing import Tuple, Optional

class VCSManager:
    """
    Manages VCS (Git/SVN) synchronization for the project.
    OmegaT team projects typically use a .repositories/ folder for the local checkout.
    """
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.repo_dir = os.path.join(project_dir, ".noveltrad", ".repositories")
        
    def _ensure_dir(self, path: str):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    def run_cmd(self, cmd: list, cwd: str) -> Tuple[bool, str]:
        """Runs a subprocess command and returns success, output/error."""
        try:
            # We use creationflags=0x08000000 on Windows to hide console window if needed,
            # but for now standard subprocess run is fine.
            res = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
            return True, res.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except FileNotFoundError:
            tool = cmd[0]
            return False, f"L'outil '{tool}' n'est pas installé ou n'est pas dans le PATH."

    def init_git(self, remote_url: str) -> Tuple[bool, str]:
        """Initializes a Git repository in .repositories/git and sets the remote."""
        git_dir = os.path.join(self.repo_dir, "git")
        self._ensure_dir(git_dir)
        
        # Check if already a git repo
        if not os.path.exists(os.path.join(git_dir, ".git")):
            success, msg = self.run_cmd(["git", "init"], git_dir)
            if not success: return False, msg
            
        # Set remote
        success, msg = self.run_cmd(["git", "remote", "add", "origin", remote_url], git_dir)
        if not success:
            # Maybe remote already exists
            success2, msg2 = self.run_cmd(["git", "remote", "set-url", "origin", remote_url], git_dir)
            if not success2: return False, msg2
            
        return True, "Git initialisé avec le dépôt distant."

    def sync_git(self, action: str = "pull", commit_msg: str = "Auto-sync") -> Tuple[bool, str]:
        """Pulls or Pushes to the Git remote."""
        git_dir = os.path.join(self.repo_dir, "git")
        if not os.path.exists(os.path.join(git_dir, ".git")):
            return False, "Le dépôt Git n'est pas initialisé."
            
        if action == "pull":
            return self.run_cmd(["git", "pull", "origin", "main", "--rebase"], git_dir)
        elif action == "push":
            # Add all, commit, push
            self.run_cmd(["git", "add", "."], git_dir)
            self.run_cmd(["git", "commit", "-m", commit_msg], git_dir)
            return self.run_cmd(["git", "push", "origin", "main"], git_dir)
        else:
            return False, "Action invalide. Utilisez 'pull' ou 'push'."

    def init_svn(self, repo_url: str) -> Tuple[bool, str]:
        """Checks out an SVN repository."""
        svn_dir = os.path.join(self.repo_dir, "svn")
        self._ensure_dir(svn_dir)
        
        if not os.path.exists(os.path.join(svn_dir, ".svn")):
            return self.run_cmd(["svn", "checkout", repo_url, "."], svn_dir)
            
        return True, "SVN déjà initialisé."

    def sync_svn(self, action: str = "update", commit_msg: str = "Auto-sync") -> Tuple[bool, str]:
        """Updates or Commits to the SVN remote."""
        svn_dir = os.path.join(self.repo_dir, "svn")
        if not os.path.exists(os.path.join(svn_dir, ".svn")):
            return False, "Le dépôt SVN n'est pas initialisé."
            
        if action == "update":
            return self.run_cmd(["svn", "update"], svn_dir)
        elif action == "commit":
            self.run_cmd(["svn", "add", "--force", "."], svn_dir)
            return self.run_cmd(["svn", "commit", "-m", commit_msg], svn_dir)
        else:
            return False, "Action invalide. Utilisez 'update' ou 'commit'."
