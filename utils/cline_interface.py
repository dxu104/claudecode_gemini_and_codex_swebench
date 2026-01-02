import os
import subprocess
from typing import Dict, List

class ClineCodeInterface:
    """Interface for interacting with the Cline CLI."""

    def __init__(self):
        """Ensure the Cline CLI is available on the system."""
        try:
            result = subprocess.run(["cline", "version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    "Cline CLI not found. Please ensure 'cline' is installed and in PATH"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Cline CLI not found. Please ensure 'cline' is installed and in PATH"
            )

    def execute_code_cli(self, prompt: str, cwd: str, model: str = None) -> Dict[str, any]:
        """Execute Cline via CLI and capture the response.
        
        Args:
            prompt: The prompt to send to Cline (passed as positional argument).
            cwd: Working directory to execute in.
            model: Optional model parameter (IGNORED for Cline).
                   Cline does not support setting model via task settings (-s model=).
                   Models must be configured via 'cline auth' command.
                   This parameter is kept for API compatibility but has no effect.
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)

            # Build command with proper Cline CLI syntax
            # -y: auto-confirm
            # -F plain: plain text output format
            # --oneshot: execute task once without interactive mode (suitable for automation)
            cmd = ["cline", "-y", "-F", "plain", "--oneshot"]
            
            # Note: Cline does not support setting model via -s model= task setting.
            # The error "unsupported field 'model'" occurs if we try to use it.
            # Models must be configured via 'cline auth' command (e.g., cline auth -p openai-native -k KEY -m gpt-5).
            # Cline will use the default configured model from auth settings.
            # The model parameter is ignored to maintain API compatibility with other backends.
            # if model:
            #     cmd.extend(["-s", f"model={model}"])
            
            # Prompt is passed as positional argument (not via stdin)
            cmd.append(prompt)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes - Cline may need more time for complex tasks
            )

            os.chdir(original_cwd)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired as e:
            os.chdir(original_cwd)
            # Try to get partial output if available
            partial_stdout = getattr(e, 'stdout', '') or ''
            partial_stderr = getattr(e, 'stderr', '') or ''
            
            timeout_msg = "Command timed out after 30 minutes"
            if partial_stdout or partial_stderr:
                timeout_msg += f". Partial output - stdout: {len(partial_stdout)} chars, stderr: {len(partial_stderr)} chars"
            
            return {
                "success": False,
                "stdout": partial_stdout,
                "stderr": timeout_msg + (f"\nPartial stderr: {partial_stderr[:500]}" if partial_stderr else ""),
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
        """Extract file changes from Cline's response (placeholder)."""
        return []

