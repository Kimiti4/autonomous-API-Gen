import subprocess
import random
import time
from typing import Optional, Tuple, Dict
from app.core.logger import logger


class DockerRunner:
    """Manages Docker container lifecycle for generated APIs."""

    def __init__(self):
        self.containers = {}

    def build_and_run(self, build_dir: str, container_name: str = None, environment: Optional[Dict[str, str]] = None) -> Tuple[bool, int, str]:
        """Build and run a generated API with optional environment variables."""
        if not container_name:
            container_name = f"evo-api-{random.randint(1000, 9999)}"
        port = random.randint(8001, 9000)
        environment = environment or {}
        try:
            build_result = subprocess.run(["docker", "build", "-t", container_name, build_dir], capture_output=True, text=True, timeout=300)
            if build_result.returncode != 0:
                return False, 0, f"Docker build failed: {build_result.stderr}"
            run_command = ["docker", "run", "-d", "--name", container_name, "-p", f"{port}:8000"]
            for key, value in environment.items():
                run_command.extend(["-e", f"{key}={value}"])
            run_command.append(container_name)
            run_result = subprocess.run(run_command, capture_output=True, text=True, timeout=60)
            if run_result.returncode != 0:
                return False, 0, f"Docker run failed: {run_result.stderr}"
            self.containers[container_name] = {"id": run_result.stdout.strip(), "port": port, "build_dir": build_dir}
            time.sleep(3)
            return True, port, ""
        except subprocess.TimeoutExpired:
            return False, 0, "Docker operation timed out"
        except Exception as e:
            logger.error("Docker error", exc_info=True)
            return False, 0, f"Docker error: {e}"

    def test_api(self, port: int, timeout: int = 10) -> bool:
        """Test if API is responding on given port."""
        import httpx
        try:
            with httpx.Client(timeout=timeout) as client:
                return client.get(f"http://localhost:{port}/").status_code == 200
        except Exception:
            return False

    def stop_container(self, container_name: str) -> bool:
        """Stop and remove a container."""
        try:
            subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=30)
            subprocess.run(["docker", "rm", container_name], capture_output=True, timeout=30)
            self.containers.pop(container_name, None)
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            return False

    def cleanup_all(self):
        """Stop all tracked containers."""
        for container_name in list(self.containers.keys()):
            self.stop_container(container_name)
