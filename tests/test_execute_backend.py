"""Unit tests for LocalExecutionBackend.

Tests cover:
- Successful command execution with correct exit codes
- Timeout handling for long-running commands
- Output truncation for large outputs
- Working directory correctness
- Combined stdout/stderr output
- Stable ID property
"""

import tempfile
from pathlib import Path

import pytest

from agent.backend_local_exec import LocalExecutionBackend


class TestLocalExecutionBackend:
    """Test suite for LocalExecutionBackend execution capabilities."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def backend(self, temp_workspace):
        """Create a LocalExecutionBackend instance for testing."""
        return LocalExecutionBackend(
            root_dir=temp_workspace,
            default_timeout=5,  # Short timeout for tests
            max_output_chars=1000,  # Small limit for truncation tests
        )

    def test_successful_command_execution(self, backend):
        """Test that successful commands return correct exit code and output."""
        result = backend.execute("echo 'Hello, World!'")
        
        assert result.exit_code == 0
        assert "Hello, World!" in result.output
        assert result.truncated is False

    def test_command_exit_code(self, backend):
        """Test that non-zero exit codes are captured correctly."""
        result = backend.execute("exit 42")
        
        assert result.exit_code == 42

    def test_timeout_handling(self, backend):
        """Test that long-running commands timeout with exit code 124."""
        # Command that sleeps longer than the timeout (5 seconds)
        result = backend.execute("sleep 10")
        
        assert result.exit_code == 124
        assert "timed out" in result.output.lower()
        assert result.truncated is False

    def test_output_truncation(self, backend):
        """Test that large outputs are truncated with middle section removed."""
        # Generate output larger than max_output_chars (1000)
        # Python command to print 2000 characters
        result = backend.execute("python3 -c \"print('A' * 2000)\"")
        
        assert result.truncated is True
        assert len(result.output) <= 1200  # Should be around max_output_chars
        assert "[truncated]" in result.output

    def test_working_directory(self, backend, temp_workspace):
        """Test that commands execute in the correct working directory."""
        # Create a marker file in the workspace
        marker_file = temp_workspace / "marker.txt"
        marker_file.write_text("test")
        
        # List files in current directory - should see marker.txt
        result = backend.execute("ls")
        
        assert result.exit_code == 0
        assert "marker.txt" in result.output

    def test_combined_stdout_stderr(self, backend):
        """Test that both stdout and stderr are captured in output."""
        # Command that outputs to both stdout and stderr
        cmd = "echo 'stdout message' && echo 'stderr message' >&2"
        result = backend.execute(cmd)
        
        assert result.exit_code == 0
        assert "stdout message" in result.output
        assert "stderr message" in result.output

    def test_id_property(self, backend, temp_workspace):
        """Test that the id property returns a stable identifier."""
        backend_id = backend.id
        
        assert backend_id is not None
        assert backend_id.startswith("local-exec-")
        assert temp_workspace.name in backend_id
        
        # ID should be consistent across multiple calls
        assert backend.id == backend_id

    def test_stderr_only_command(self, backend):
        """Test command that only outputs to stderr."""
        result = backend.execute("echo 'error' >&2")
        
        assert result.exit_code == 0
        assert "error" in result.output

    def test_relative_path_resolution(self, backend, temp_workspace):
        """Test that relative paths work correctly within the workspace."""
        # Create a subdirectory
        subdir = temp_workspace / "subdir"
        subdir.mkdir()
        
        # Create a file in subdirectory
        test_file = subdir / "test.txt"
        test_file.write_text("content")
        
        # Read file using relative path
        result = backend.execute("cat subdir/test.txt")
        
        assert result.exit_code == 0
        assert "content" in result.output

    def test_full_environment_inheritance(self, backend):
        """Test that subprocess inherits all environment variables from parent."""
        # Set a test environment variable in the parent process
        import os
        os.environ["TEST_CUSTOM_VAR"] = "test_value_123"
        
        # The subprocess should have access to it
        result = backend.execute("echo $TEST_CUSTOM_VAR")
        assert result.exit_code == 0
        assert "test_value_123" in result.output
        
        # Cleanup
        del os.environ["TEST_CUSTOM_VAR"]

    def test_command_with_pipes(self, backend):
        """Test that shell features like pipes work correctly."""
        result = backend.execute("echo 'hello' | tr 'h' 'H'")
        
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_multiline_output(self, backend):
        """Test that multiline output is captured correctly."""
        result = backend.execute("echo 'line1' && echo 'line2' && echo 'line3'")
        
        assert result.exit_code == 0
        assert "line1" in result.output
        assert "line2" in result.output
        assert "line3" in result.output

