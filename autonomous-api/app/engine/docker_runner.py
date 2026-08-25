import subprocess
import random
import time
import os
from typing import Optional, Tuple
from app.core.logger import logger


class DockerRunner:
    """Manages Docker container lifecycle for generated APIs"""
    
    def __init__(self):
        self.containers = {}  # Track running containers
    
    def build_and_run(self, build_dir: str, container_name: str = None) -> Tuple[bool, int, str]:
        """
        Build Docker image and run container.
        
        Returns:
            Tuple of (success, port, error_message)
        """
        if not container_name:
            container_name = f"evo-api-{random.randint(1000, 9999)}"
        
        port = random.randint(8001, 9000)
        
        try:
            # Build the image
            logger.info(f"Building Docker image in {build_dir}")
            build_result = subprocess.run(
                ["docker", "build", "-t", container_name, build_dir],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if build_result.returncode != 0:
                error_msg = f"Docker build failed: {build_result.stderr}"
                logger.error(error_msg)
                return False, 0, error_msg
            
            logger.info(f"Docker image built successfully: {container_name}")
            
            # Run the container
            logger.info(f"Running container on port {port}")
            run_result = subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", container_name,
                    "-p", f"{port}:8000",
                    container_name
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if run_result.returncode != 0:
                error_msg = f"Docker run failed: {run_result.stderr}"
                logger.error(error_msg)
                return False, 0, error_msg
            
            container_id = run_result.stdout.strip()
            self.containers[container_name] = {
                "id": container_id,
                "port": port,
                "build_dir": build_dir
            }
            
            logger.info(f"Container started: {container_name} on port {port}")
            
            # Wait for container to be ready
            time.sleep(3)
            
            return True, port, ""
            
        except subprocess.TimeoutExpired:
            error_msg = "Docker operation timed out"
            logger.error(error_msg)
            return False, 0, error_msg
        except Exception as e:
            error_msg = f"Docker error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, 0, error_msg
    
    def test_api(self, port: int, timeout: int = 10) -> bool:
        """Test if API is responding on given port"""
        import httpx
        
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"http://localhost:{port}/")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"API test failed on port {port}: {str(e)}")
            return False
    
    def stop_container(self, container_name: str) -> bool:
        """Stop and remove a container"""
        try:
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                timeout=30
            )
            subprocess.run(
                ["docker", "rm", container_name],
                capture_output=True,
                timeout=30
            )
            
            if container_name in self.containers:
                del self.containers[container_name]
            
            logger.info(f"Container stopped: {container_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {str(e)}")
            return False
    
    def cleanup_all(self):
        """Stop all tracked containers"""
        for container_name in list(self.containers.keys()):
            self.stop_container(container_name)
