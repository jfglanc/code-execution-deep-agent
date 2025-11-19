# Docker Execution Backend

This directory contains the Docker-based execution backend for the Code Execution Deep Agent.

## Contents

- **`backend.py`**: `DockerExecutionBackend` implementation that executes commands inside a Docker container
- **`Dockerfile`**: Container definition for the execution environment

## Building the Container

From the project root:

```bash
docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .
```

## Starting the Container

```bash
docker run -d --name code-execution-agent \
  -v "$(pwd)/workspace:/workspace" \
  code-execution-agent:latest
```

## Container Architecture

The container provides:
- Python 3.11 runtime
- Pre-installed data science packages (pandas, numpy, matplotlib, etc.)
- Filesystem structure with symlinks:
  - `/data` → `/workspace/data`
  - `/scripts` → `/workspace/scripts`
  - `/results` → `/workspace/results`
- Static copy of `/skills/` directory

## Volume Mounting

The local `workspace/` directory is mounted to `/workspace` in the container, providing:
- Real-time bidirectional file synchronization
- Persistent storage across container restarts
- Direct access to agent-generated files

See `docs/docker-setup.md` for detailed setup and troubleshooting.

