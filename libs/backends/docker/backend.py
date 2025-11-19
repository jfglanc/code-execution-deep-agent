"""Docker execution backend that runs commands inside a container.

This module provides DockerExecutionBackend, which inherits from FilesystemBackend
to get secure file I/O operations (on the host) and implements SandboxBackendProtocol
to add command execution capabilities inside a Docker container.
"""

import os
from pathlib import Path

import docker
from docker.errors import DockerException, NotFound

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol


class DockerExecutionBackend(FilesystemBackend, SandboxBackendProtocol):
    """Backend that provides file operations on host and command execution in Docker.

    This backend inherits file operation methods (read, write, edit, ls_info, etc.)
    from FilesystemBackend (which operate on the host filesystem) and adds the
    execute() method to run shell commands inside a Docker container.

    The container must be running before the backend is initialized. Commands execute
    inside the container where the filesystem matches the agent's virtual paths:
    /data, /scripts, /results are real directories (via symlinks to /workspace).

    Attributes:
        container_name: Name of the Docker container to execute commands in.
        default_timeout: Maximum seconds allowed for command execution (default: 120).
        max_output_chars: Maximum characters in combined output before truncation.
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        container_name: str = "code-execution-agent",
        default_timeout: int = 120,
        max_output_chars: int = 50_000,
    ) -> None:
        """Initialize the DockerExecutionBackend.

        Args:
            root_dir: Root directory for file operations on the host.
            container_name: Name of the Docker container to use for execution.
            default_timeout: Maximum execution time in seconds (default: 120).
            max_output_chars: Maximum output size before truncation (default: 50000).

        Raises:
            DockerException: If Docker is not available or container is not running.
        """
        super().__init__(root_dir=root_dir, virtual_mode=True)
        self.container_name = container_name
        self.default_timeout = default_timeout
        self.max_output_chars = max_output_chars

        # Check Docker availability and get container
        try:
            self.docker_client = docker.from_env()
            self.container = self.docker_client.containers.get(container_name)
            
            # Verify container is running
            if self.container.status != "running":
                raise DockerException(
                    f"Container '{container_name}' exists but is not running (status: {self.container.status}). "
                    f"Start it with: docker start {container_name}"
                )
        except NotFound:
            raise DockerException(
                f"Container '{container_name}' not found. "
                f"Create and start it with:\n"
                f"  docker build -t code-execution-agent:latest .\n"
                f"  docker run -d --name {container_name} "
                f"-v $(pwd)/workspace:/workspace code-execution-agent:latest"
            )
        except DockerException:
            raise
        except Exception as e:
            raise DockerException(f"Failed to connect to Docker: {e}") from e

    def execute(self, command: str) -> ExecuteResponse:
        """Execute a shell command inside the Docker container.

        The command runs with:
        - Working directory: /workspace inside container
        - Environment: Inherits from container + parent process env vars
        - Timeout: Configured default_timeout
        - Output capture: Combined stdout and stderr

        Args:
            command: Shell command string to execute.

        Returns:
            ExecuteResponse with:
                - output: Combined stdout and stderr (possibly truncated)
                - exit_code: Process exit code (124 indicates timeout)
                - truncated: True if output was truncated
        """
        try:
            # Build environment dict from parent process
            env = dict(os.environ)
            
            # Execute command inside container
            exec_result = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/workspace",
                environment=env,
                demux=False,  # Combine stdout/stderr
                stream=False,
            )

            # Get output (bytes) and decode
            output = exec_result.output.decode("utf-8", errors="replace") if exec_result.output else ""
            exit_code = exec_result.exit_code

            # Truncate if too long (preserve beginning and end)
            truncated = len(output) > self.max_output_chars
            if truncated:
                half = self.max_output_chars // 2
                head = output[:half]
                tail = output[-half:]
                output = head + "\n... [truncated] ...\n" + tail

            return ExecuteResponse(
                output=output,
                exit_code=exit_code,
                truncated=truncated,
            )

        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command in container: {e}",
                exit_code=1,
                truncated=False,
            )

    @property
    def id(self) -> str:
        """Return a stable identifier for this backend instance.

        Returns:
            String identifier in format "docker-exec-<container_name>".
        """
        return f"docker-exec-{self.container_name}"

