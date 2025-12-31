import os
import subprocess
from typing import Dict, List

class CodexCodeInterface:
    """Interface for interacting with the Codex CLI."""

    def __init__(self):
        """Ensure the Codex CLI is available on the system."""
        try:
            result = subprocess.run(["codex", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    "Codex CLI not found. Please ensure 'codex' is installed and in PATH"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Codex CLI not found. Please ensure 'codex' is installed and in PATH"
            )

    def execute_code_cli(self, prompt: str, cwd: str, model: str = None) -> Dict[str, any]:
        """Execute Codex via CLI and capture the response.
        
        Uses 'codex exec' command for non-interactive execution, which is the
        recommended way to run Codex CLI programmatically.
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)
            
            # Use 'exec' subcommand for non-interactive execution
            cmd = ["codex", "exec"]
            if model:
                cmd.extend(["--model", model])
            
            # Add convenience flags for automatic execution
            # --full-auto: low-friction sandboxed automatic execution
            cmd.append("--full-auto")
            
            # Execute codex exec with the prompt via stdin
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=cwd
            )
            
            os.chdir(original_cwd)
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
                
        except subprocess.TimeoutExpired:
            os.chdir(original_cwd)
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out after 10 minutes",
                "returncode": -1,
            }
        except Exception as e:
            os.chdir(original_cwd)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    def extract_file_changes(self, response: str) -> List[Dict[str, str]]:
        """Extract file changes from Codex's response (placeholder)."""
        return []
