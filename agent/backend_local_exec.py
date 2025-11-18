"""Local execution backend that extends FilesystemBackend with command execution.

This module provides LocalExecutionBackend, which inherits from FilesystemBackend
to get secure file I/O operations and implements SandboxBackendProtocol to add
local command execution capabilities.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol

from agent.virtualfs import VirtualPathResolver


class LocalExecutionBackend(FilesystemBackend, SandboxBackendProtocol):
    """Backend that provides both file operations and local command execution.

    This backend inherits file operation methods (read, write, edit, ls_info, etc.)
    from FilesystemBackend and adds the execute() method to run shell commands
    locally with proper safety constraints.

    Subprocesses inherit the full environment from the parent process, including
    all environment variables loaded from .env files. This allows scripts to access
    API keys, configuration variables, and other environment-based settings.

    Attributes:
        default_timeout: Maximum seconds allowed for command execution (default: 120).
        max_output_chars: Maximum characters in combined output before truncation (default: 50000).
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        default_timeout: int = 120,
        max_output_chars: int = 50_000,
        virtual_mode: bool = False,
        virtual_resolver: Optional[VirtualPathResolver] = None,
    ) -> None:
        """Initialize the LocalExecutionBackend.

        Args:
            root_dir: Root directory for file operations and command execution.
                     Commands will run with cwd=root_dir.
            default_timeout: Maximum execution time in seconds (default: 120).
            max_output_chars: Maximum output size before truncation (default: 50000).
            virtual_mode: If True, treat paths as virtual (relative to root_dir).
                         If False, absolute paths are used as-is on filesystem.
        """
        super().__init__(root_dir=root_dir, virtual_mode=virtual_mode)
        self.default_timeout = default_timeout
        self.max_output_chars = max_output_chars
        self.virtual_resolver = virtual_resolver

    def execute(self, command: str) -> ExecuteResponse:
        """Execute a shell command in the backend's working directory.

        The command runs with:
        - cwd set to self.cwd (the backend's root directory)
        - Full environment inheritance from parent process (includes .env variables)
        - Configured timeout to prevent hanging
        - Output capture of both stdout and stderr

        Args:
            command: Shell command string to execute.

        Returns:
            ExecuteResponse with:
                - output: Combined stdout and stderr (possibly truncated)
                - exit_code: Process exit code (124 indicates timeout)
                - truncated: True if output was truncated
        """
        if self.virtual_mode and self.virtual_resolver:
            command = self.virtual_resolver.rewrite_command(command)

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
                env=self._build_env(),
            )

            # Combine stdout and stderr
            output = proc.stdout or ""
            if proc.stderr:
                output += ("\n" if output else "") + proc.stderr

            # Truncate if too long (preserve beginning and end)
            truncated = len(output) > self.max_output_chars
            if truncated:
                half = self.max_output_chars // 2
                head = output[:half]
                tail = output[-half:]
                output = head + "\n... [truncated] ...\n" + tail

            return ExecuteResponse(
                output=output,
                exit_code=proc.returncode,
                truncated=truncated,
            )

        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Command timed out after {self.default_timeout}s",
                exit_code=124,  # Standard timeout exit code
                truncated=False,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command: {e}",
                exit_code=1,
                truncated=False,
            )

    def _build_env(self) -> dict[str, str]:
        """Build the environment dictionary for subprocess execution.

        Returns a complete copy of the parent process's environment variables,
        including all variables loaded from .env files. This allows subprocesses
        to access API keys, configuration variables, and other environment-based
        settings.

        Returns:
            Dictionary of all environment variables from parent process.
        """
        return dict(os.environ)

    @property
    def id(self) -> str:
        """Return a stable identifier for this backend instance.

        Returns:
            String identifier in format "local-exec-<directory_name>".
        """
        return f"local-exec-{self.cwd.name}"

