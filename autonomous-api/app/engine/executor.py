import subprocess
import tempfile
import os


def run_code(code: str):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
        f.write(code.encode())
        temp_path = f.name

        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=3
            )
            return {
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "success": result.returncode == 0
            }
        finally:
            os.remove(temp_path)