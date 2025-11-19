# Docker Setup Guide

This guide explains how to set up and manage the Docker execution environment for the Code Execution Deep Agent.

## Overview

The agent executes commands inside a Docker container to provide:
- **Consistent paths**: `/data`, `/scripts`, `/results` work in both file operations and executed code
- **Isolation**: Scripts run in a sandboxed environment
- **Persistence**: Installed packages (via `pip install`) persist between commands
- **Pre-installed tools**: Common data science libraries are ready to use

## Prerequisites

- Docker Desktop installed and running
- Docker CLI accessible from terminal

## Initial Setup

### 1. Build the Docker Image

From the project root directory, build the custom image:

```bash
docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .
```

This creates an image with:
- Python 3.11
- Pre-installed packages: pandas, numpy, matplotlib, seaborn, scipy, requests, pypdf, reportlab, pyyaml
- Symlinks for `/data` → `/workspace/data`, `/scripts` → `/workspace/scripts`, `/results` → `/workspace/results`
- Static copy of the `/skills` directory

**Note**: Rebuild the image whenever you modify skills:
```bash
docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .
```

### 2. Start the Container

Start the container with the workspace mounted:

```bash
docker run -d \
  --name code-execution-agent \
  -v "$(pwd)/workspace:/workspace" \
  code-execution-agent:latest
```

**Explanation:**
- `-d`: Run in detached mode (background)
- `--name code-execution-agent`: Container name (must match `CONTAINER_NAME` in `agent/config.py`)
- `-v $(pwd)/workspace:/workspace`: Mount local `workspace/` to `/workspace` in container
- `code-execution-agent:latest`: The image to use

**On Windows (PowerShell):**
```powershell
docker run -d `
  --name code-execution-agent `
  -v "${PWD}/workspace:/workspace" `
  code-execution-agent:latest
```

## Managing the Container

### Check Container Status

```bash
docker ps -a --filter name=code-execution-agent
```

Look for `STATUS` column - should say "Up X minutes/hours".

### Stop the Container

```bash
docker stop code-execution-agent
```

### Start the Container

```bash
docker start code-execution-agent
```

### Restart the Container

```bash
docker restart code-execution-agent
```

### Remove the Container

```bash
docker stop code-execution-agent
docker rm code-execution-agent
```

Then recreate it with the `docker run` command above.

## Installing Additional Packages

If the agent needs a package that's not pre-installed:

### Option 1: Let the Agent Install It

The agent can run:
```python
execute("pip install package-name")
```

The package persists in the container until it's stopped/removed.

### Option 2: Add to Dockerfile (Permanent)

1. Edit `libs/backends/docker/Dockerfile` and add the package to the `RUN pip install` line
2. Rebuild: `docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .`
3. Recreate container: `docker stop code-execution-agent && docker rm code-execution-agent`
4. Start new container: `docker run -d --name code-execution-agent -v $(pwd)/workspace:/workspace code-execution-agent:latest`

## Troubleshooting

### Error: Container 'code-execution-agent' not found

**Solution:** The container hasn't been created yet. Run the `docker run` command from step 2 above.

### Error: Container exists but is not running

**Solution:** Start it:
```bash
docker start code-execution-agent
```

### Error: Cannot connect to Docker daemon

**Solution:** Ensure Docker Desktop is running.

On Mac:
```bash
open -a Docker
```

On Linux:
```bash
sudo systemctl start docker
```

### Files Not Appearing in Container

**Issue:** Changes to `workspace/` on host don't appear in container.

**Solution:** The volume mount is live - changes should appear immediately. If not:
1. Check the mount path is correct: `docker inspect code-execution-agent | grep Mounts -A 10`
2. Restart the container: `docker restart code-execution-agent`

### Skills Not Updated

**Issue:** Modified a skill but changes don't appear.

**Solution:** Skills are copied into the image at build time (static). Rebuild the image:
```bash
docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .
docker stop code-execution-agent
docker rm code-execution-agent
docker run -d --name code-execution-agent -v $(pwd)/workspace:/workspace code-execution-agent:latest
```

## Advanced: Interactive Shell Access

To explore the container's environment or debug issues:

```bash
docker exec -it code-execution-agent /bin/bash
```

Inside the container:
- Check paths: `ls /data /scripts /results /skills`
- Verify symlinks: `ls -la / | grep workspace`
- Test Python: `python3 -c "import pandas; print(pandas.__version__)"`
- Exit: `exit`

## Filesystem Layout

**Inside Container:**
```
/
├── data/           → symlink to /workspace/data
├── scripts/        → symlink to /workspace/scripts
├── results/        → symlink to /workspace/results
├── skills/         → static copy from build
└── workspace/      → mounted from host
    ├── data/       → actual files (shared with host)
    ├── scripts/    → actual files (shared with host)
    └── results/    → actual files (shared with host)
```

**On Host:**
```
project/
├── workspace/
│   ├── data/       ← mounted into container
│   ├── scripts/    ← mounted into container
│   └── results/    ← mounted into container
└── skills/         ← copied into image at build time
```

## Clean Slate Reset

To completely reset the execution environment:

```bash
# Remove container
docker stop code-execution-agent
docker rm code-execution-agent

# Remove image (forces rebuild)
docker rmi code-execution-agent:latest

# Rebuild and restart
docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .
docker run -d --name code-execution-agent -v $(pwd)/workspace:/workspace code-execution-agent:latest
```

## Additional Information

For more details on the architecture and implementation, see:
- `docs/architecture.md` - Technical architecture and design decisions
- `libs/backends/docker/README.md` - Docker backend implementation details
- Main `README.md` - Quick start guide and usage examples

