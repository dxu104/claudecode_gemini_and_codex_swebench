import os
import subprocess
import pty
import select
import time
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
        
        Codex CLI requires an interactive terminal (TTY), so we use a pseudo-terminal
        to simulate one for non-interactive execution.
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)
            
            cmd = ["codex"]
            if model:
                cmd.extend(["--model", model])
            
            # Create a pseudo-terminal for Codex CLI (it requires TTY)
            master_fd, slave_fd = pty.openpty()
            
            try:
                # Start the process with pseudo-terminal
                process = subprocess.Popen(
                    cmd,
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    text=False,
                    preexec_fn=os.setsid,
                    cwd=cwd
                )
                
                # Close slave_fd in parent process
                os.close(slave_fd)
                
                # Send the prompt
                prompt_bytes = (prompt + "\n").encode('utf-8')
                os.write(master_fd, prompt_bytes)
                
                # Read output with timeout
                stdout_data = []
                timeout = 600  # 10 minutes
                start_time = time.time()
                
                while True:
                    if time.time() - start_time > timeout:
                        process.terminate()
                        os.chdir(original_cwd)
                        os.close(master_fd)
                        return {
                            "success": False,
                            "stdout": "",
                            "stderr": "Command timed out after 10 minutes",
                            "returncode": -1,
                        }
                    
                    if process.poll() is not None:
                        # Process has finished
                        break
                    
                    # Check if there's data to read
                    if select.select([master_fd], [], [], 0.1)[0]:
                        try:
                            data = os.read(master_fd, 4096)
                            if data:
                                stdout_data.append(data)
                        except OSError:
                            break
                
                # Read any remaining output
                while True:
                    if select.select([master_fd], [], [], 0.1)[0]:
                        try:
                            data = os.read(master_fd, 4096)
                            if not data:
                                break
                            stdout_data.append(data)
                        except OSError:
                            break
                    else:
                        break
                
                stdout = b''.join(stdout_data).decode('utf-8', errors='ignore')
                returncode = process.wait()
                
                os.chdir(original_cwd)
                os.close(master_fd)
                
                return {
                    "success": returncode == 0,
                    "stdout": stdout,
                    "stderr": "",
                    "returncode": returncode,
                }
                
            except Exception as e:
                try:
                    os.close(master_fd)
                except:
                    pass
                os.chdir(original_cwd)
                raise e
                
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
