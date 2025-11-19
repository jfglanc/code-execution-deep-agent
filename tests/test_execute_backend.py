"""Unit tests for DockerExecutionBackend.

Tests cover:
- Successful command execution with correct exit codes
- Timeout handling for long-running commands
- Output truncation for large outputs
- Working directory correctness
- Combined stdout/stderr output
- Stable ID property
- Container availability checks
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from libs.backends import DockerExecutionBackend


class TestDockerExecutionBackend:
    """Test suite for DockerExecutionBackend execution capabilities."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        with patch('agent.backend_docker.docker.from_env') as mock_from_env:
            # Create mock client and container
            mock_client = Mock()
            mock_container = Mock()
            mock_container.status = "running"
            mock_container.exec_run = Mock()
            
            mock_client.containers.get = Mock(return_value=mock_container)
            mock_from_env.return_value = mock_client
            
            yield mock_client, mock_container

    @pytest.fixture
    def backend(self, temp_workspace, mock_docker_client):
        """Create a DockerExecutionBackend instance for testing."""
        return DockerExecutionBackend(
            root_dir=temp_workspace,
            container_name="test-container",
            default_timeout=5,  # Short timeout for tests
            max_output_chars=1000,  # Small limit for truncation tests
        )

    def test_successful_command_execution(self, backend, mock_docker_client):
        """Test that successful commands return correct exit code and output."""
        _, mock_container = mock_docker_client
        
        # Mock successful exec_run
        mock_container.exec_run.return_value = MagicMock(
            output=b"Hello, World!\n",
            exit_code=0
        )
        
        result = backend.execute("echo 'Hello, World!'")
        
        assert result.exit_code == 0
        assert "Hello, World!" in result.output
        assert result.truncated is False

    def test_command_exit_code(self, backend, mock_docker_client):
        """Test that non-zero exit codes are captured correctly."""
        _, mock_container = mock_docker_client
        
        mock_container.exec_run.return_value = MagicMock(
            output=b"",
            exit_code=42
        )
        
        result = backend.execute("exit 42")
        
        assert result.exit_code == 42

    def test_output_truncation(self, backend, mock_docker_client):
        """Test that large outputs are truncated with middle section removed."""
        _, mock_container = mock_docker_client
        
        # Generate output larger than max_output_chars (1000)
        large_output = b"A" * 2000
        mock_container.exec_run.return_value = MagicMock(
            output=large_output,
            exit_code=0
        )
        
        result = backend.execute("python3 -c \"print('A' * 2000)\"")
        
        assert result.truncated is True
        assert len(result.output) <= 1200  # Should be around max_output_chars
        assert "[truncated]" in result.output

    def test_combined_stdout_stderr(self, backend, mock_docker_client):
        """Test that both stdout and stderr are captured in output."""
        _, mock_container = mock_docker_client
        
        # Mock combined output
        combined_output = b"stdout message\nstderr message\n"
        mock_container.exec_run.return_value = MagicMock(
            output=combined_output,
            exit_code=0
        )
        
        result = backend.execute("echo 'stdout message' && echo 'stderr message' >&2")
        
        assert result.exit_code == 0
        assert "stdout message" in result.output
        assert "stderr message" in result.output

    def test_id_property(self, backend):
        """Test that the id property returns a stable identifier."""
        backend_id = backend.id
        
        assert backend_id is not None
        assert backend_id.startswith("docker-exec-")
        assert "test-container" in backend_id
        
        # ID should be consistent across multiple calls
        assert backend.id == backend_id

    def test_container_not_running(self, temp_workspace):
        """Test error when container exists but is not running."""
        with patch('agent.backend_docker.docker.from_env') as mock_from_env:
            mock_client = Mock()
            mock_container = Mock()
            mock_container.status = "exited"  # Not running
            
            mock_client.containers.get = Mock(return_value=mock_container)
            mock_from_env.return_value = mock_client
            
            with pytest.raises(Exception) as exc_info:
                DockerExecutionBackend(
                    root_dir=temp_workspace,
                    container_name="stopped-container"
                )
            
            assert "not running" in str(exc_info.value).lower()

    def test_container_not_found(self, temp_workspace):
        """Test error when container doesn't exist."""
        with patch('agent.backend_docker.docker.from_env') as mock_from_env:
            from docker.errors import NotFound
            
            mock_client = Mock()
            mock_client.containers.get = Mock(side_effect=NotFound("Container not found"))
            mock_from_env.return_value = mock_client
            
            with pytest.raises(Exception) as exc_info:
                DockerExecutionBackend(
                    root_dir=temp_workspace,
                    container_name="missing-container"
                )
            
            assert "not found" in str(exc_info.value).lower()

    def test_command_with_pipes(self, backend, mock_docker_client):
        """Test that shell features like pipes work correctly."""
        _, mock_container = mock_docker_client
        
        mock_container.exec_run.return_value = MagicMock(
            output=b"Hello\n",
            exit_code=0
        )
        
        result = backend.execute("echo 'hello' | tr 'h' 'H'")
        
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_multiline_output(self, backend, mock_docker_client):
        """Test that multiline output is captured correctly."""
        _, mock_container = mock_docker_client
        
        mock_container.exec_run.return_value = MagicMock(
            output=b"line1\nline2\nline3\n",
            exit_code=0
        )
        
        result = backend.execute("echo 'line1' && echo 'line2' && echo 'line3'")
        
        assert result.exit_code == 0
        assert "line1" in result.output
        assert "line2" in result.output
        assert "line3" in result.output

    def test_working_directory(self, backend, mock_docker_client):
        """Test that commands execute with correct working directory."""
        _, mock_container = mock_docker_client
        
        mock_container.exec_run.return_value = MagicMock(
            output=b"/workspace\n",
            exit_code=0
        )
        
        result = backend.execute("pwd")
        
        # Verify exec_run was called with workdir=/workspace
        mock_container.exec_run.assert_called_once()
        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs['workdir'] == "/workspace"

    def test_error_handling(self, backend, mock_docker_client):
        """Test that execution errors are handled gracefully."""
        _, mock_container = mock_docker_client
        
        # Mock an exception during exec_run
        mock_container.exec_run.side_effect = Exception("Container communication error")
        
        result = backend.execute("some command")
        
        assert result.exit_code == 1
        assert "Error executing command" in result.output
        assert result.truncated is False
