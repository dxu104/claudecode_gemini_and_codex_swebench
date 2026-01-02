#!/usr/bin/env python3
"""
Diagnostic tool to check if the environment is properly set up for SWE-bench.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_command(cmd, name):
    """Check if a command is available."""
    try:
        result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ {name} is installed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {name} is installed but returned error:")
            print(f"   {result.stderr}")
            return False
    except FileNotFoundError:
        print(f"❌ {name} CLI not found. Please install it.")
        return False
    except subprocess.TimeoutExpired:
        print(f"⚠️  {name} command timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {e}")
        return False

def check_python_packages():
    """Check if required Python packages are installed."""
    required = ['datasets', 'tqdm', 'jsonlines']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ Python package '{package}' is installed")
        except ImportError:
            print(f"❌ Python package '{package}' is missing")
            missing.append(package)
    
    return len(missing) == 0

def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Docker is installed: {result.stdout.strip()}")
            
            # Check if Docker daemon is running
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Docker daemon is running")
                return True
            else:
                print("❌ Docker daemon is not running")
                print("   Try: sudo systemctl start docker (Linux)")
                print("   Or start Docker Desktop (macOS/Windows)")
                return False
        else:
            print(f"❌ Docker is installed but returned error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False

def test_claude_cli():
    """Test if Claude CLI can execute a simple command."""
    print("\n🔍 Testing Claude CLI with a simple command...")
    try:
        # Try a simple command that should work
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions"],
            input="echo 'test'",
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Claude CLI executed successfully")
            return True
        else:
            print(f"❌ Claude CLI execution failed (returncode: {result.returncode})")
            if result.stderr:
                print(f"   Stderr: {result.stderr[:500]}")
            if result.stdout:
                print(f"   Stdout: {result.stdout[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  Claude CLI command timed out (this might be normal if it requires interaction)")
        return None
    except Exception as e:
        print(f"❌ Error testing Claude CLI: {e}")
        return False

def main():
    print("="*60)
    print("SWE-bench Environment Diagnostic Tool")
    print("="*60)
    print()
    
    all_ok = True
    
    # Check Python
    print("1. Checking Python...")
    python_cmd = "python3" if sys.platform != "win32" else "python"
    if check_command(python_cmd, "Python"):
        print(f"   Using: {sys.executable}")
        print(f"   Version: {sys.version}")
    else:
        all_ok = False
    print()
    
    # Check Python packages
    print("2. Checking Python packages...")
    if not check_python_packages():
        print("   Install missing packages with: pip install -r requirements.txt")
        all_ok = False
    print()
    
    # Check Code Model CLIs
    print("3. Checking Code Model CLIs...")
    claude_ok = check_command("claude", "Claude CLI")
    codex_ok = check_command("codex", "Codex CLI")
    gemini_ok = check_command("gemini", "Gemini CLI")
    cline_ok = check_command("cline", "Cline CLI")
    
    if not (claude_ok or codex_ok or gemini_ok or cline_ok):
        all_ok = False
        print("   ⚠️  No code model CLI found. Install at least one:")
        print("      - Claude: https://claude.ai/download")
        print("      - Codex: npm install -g @openai/codex")
        print("      - Gemini: Check Google's documentation")
        print("      - Cline: Check Cline's documentation")
    else:
        print("   ✅ At least one code model CLI is available")
    print()
    
    # Test Claude CLI if available
    if claude_ok:
        test_claude_cli()
    print()
    
    # Check Docker
    print("4. Checking Docker...")
    docker_ok = check_docker()
    if not docker_ok:
        all_ok = False
    print()
    
    # Check directories
    print("5. Checking project directories...")
    base_dir = Path.cwd()
    required_dirs = ["predictions", "results", "evaluation_results"]
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            print(f"✅ Directory '{dir_name}' exists")
        else:
            print(f"⚠️  Directory '{dir_name}' does not exist (will be created automatically)")
            dir_path.mkdir(parents=True, exist_ok=True)
    print()
    
    # Summary
    print("="*60)
    if all_ok:
        print("✅ All checks passed! Your environment looks good.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install Claude CLI: https://claude.ai/download")
        print("  - Install Docker: https://www.docker.com/products/docker-desktop/")
        print("  - Install Python packages: pip install -r requirements.txt")
    print("="*60)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

