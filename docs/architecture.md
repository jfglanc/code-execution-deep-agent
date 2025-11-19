# Technical Architecture: Code Execution Deep Agent

This document outlines the technical architecture and implementation details for the **Code Execution Deep Agent**. The goal is to build an agent with a "full computer" context (storage + execution) that uses **Progressive Disclosure** to manage complex skills without context bloat, and **Docker-based execution** to provide a consistent, isolated environment.

## 1. Project Overview

We are building a deep agent that executes code in an isolated Docker container while managing file operations on the host. It uses the `deepagents` framework with custom backends and middleware to provide a seamless agent experience with consistent filesystem paths.

### Core Objectives
1.  **Docker-Based Execution**: Implement a backend that runs shell commands inside a Docker container with consistent filesystem paths.
2.  **Progressive Disclosure**: Inject high-level skill metadata into the system prompt, allowing the agent to "pull" detailed instructions (`SKILL.md`) and tools (`scripts/`) only when needed.
3.  **Educational Architecture**: Demonstrate clear separation between **Middleware** (Prompt/Tool injection), **Backends** (I/O & Execution), and **Agent Graph** (Logic).
4.  **Filesystem Consistency**: Ensure paths like `/data`, `/scripts`, `/results` work identically in both file operations and executed commands.

---

## 2. Leveraged Library: `deepagents`

We are building on top of the `deepagents` library. We will leverage its specific abstractions to avoid reinventing the wheel.

### Existing Components to Use
*   **`FilesystemMiddleware`**: We will *not* rewrite this. We will use the existing middleware which provides `ls`, `read_file`, `write_file`, etc. Crucially, `FilesystemMiddleware` automatically detects if a backend implements `SandboxBackendProtocol` and injects the `execute` tool if it does.
*   **`FilesystemBackend`**: Provides secure file I/O (handling `O_NOFOLLOW`, path normalization, etc.). Our custom backend will inherit from this to inherit these safety features.
*   **`CompositeBackend`**: Allows us to mount our "Skills" directory as read-only at a virtual path (e.g., `/skills/`) while keeping the workspace read-write.
*   **`create_deep_agent`**: The main factory for wiring the LangGraph nodes, middleware, and LLM together.
*   **`BackendProtocol` & `SandboxBackendProtocol`**: The interfaces we must implement to make our custom execution backend compatible with the middleware.

---

## 3. Implemented Components

### A. `DockerExecutionBackend` (`libs/backends/docker/backend.py`)
**Role**: The interface between the Agent and the Docker container. It handles file I/O on the host and command execution inside the container.

**Location**: `libs/backends/docker/backend.py`

**Inheritance**:
```python
class DockerExecutionBackend(FilesystemBackend, SandboxBackendProtocol):
```
*   Inherits from `FilesystemBackend` to get `read`, `write`, `ls_info` implementation for free (operates on host filesystem).
*   Implements `SandboxBackendProtocol` to provide the `execute` method (runs in Docker container).

**Implementation Details**:
1.  **`execute(command: str) -> ExecuteResponse`**:
    *   Uses Docker Python SDK (`docker.from_env()`) to connect to a running container.
    *   Executes commands via `container.exec_run()` with `workdir="/workspace"`.
    *   **Environment**: Inherits full environment from parent process (including `.env` variables).
    *   **Output**: Combines `stdout` and `stderr`.
    *   **Safety**: Implements output truncation (max chars) to prevent context overflow.
2.  **`id` property**: Returns `"docker-exec-{container_name}"`.

**Docker Container** (`libs/backends/docker/Dockerfile`):
*   **Base Image**: `python:3.11-slim`
*   **Pre-installed Packages**: pandas, numpy, matplotlib, seaborn, scipy, requests, pypdf, reportlab, pyyaml
*   **Filesystem Structure**:
    *   `/workspace` - mounted from host (`workspace/` directory)
    *   `/data` → symlink to `/workspace/data`
    *   `/scripts` → symlink to `/workspace/scripts`
    *   `/results` → symlink to `/workspace/results`
    *   `/skills` - static copy from build time
*   **Volume Mount**: Host `workspace/` is mounted to container `/workspace` for real-time bidirectional sync.

### B. `SkillsMiddleware` (`libs/middleware/skills.py`)
**Role**: Implements the **Progressive Disclosure** pattern.

**Location**: `libs/middleware/skills.py`

**Inheritance**:
```python
class SkillsMiddleware(AgentMiddleware):
```

**Implementation Details**:
1.  **Initialization**: 
    *   Accepts a path to the `skills/` directory.
    *   Performs **eager skill discovery** at import time (not during agent execution).
    *   Can accept pre-discovered skills to avoid redundant filesystem scans.
2.  **Skill Discovery** (`_discover_skills`):
    *   Scans `skills/*/SKILL.md`.
    *   Parses YAML Frontmatter (Name, Description).
    *   Stores metadata including virtual paths (e.g., `/skills/csv-analytics/SKILL.md`).
3.  **`wrap_model_call` / `awrap_model_call`**:
    *   Injects a section into the System Prompt listing available skills.
    *   *Crucial*: Does NOT inject the full skill content. It instructs the agent to use `read_file` to load the specific `SKILL.md` if the description matches the user's request.
    *   Provides example workflow and usage guidelines.

---

## 4. Data Structures & Protocols

### Skills Repository Structure
The agent does not have tools hardcoded in Python. Instead, capabilities are defined in files:
```text
skills/
├── pdf-processing/
│   ├── SKILL.md               # Frontmatter + Usage Instructions
│   ├── scripts/               # Executable Python scripts
│   │   └── extract_forms.py
│   └── docs/                  # Supporting documentation
│       └── forms.md
```

**The Workflow**:
1.  **Discovery**: Middleware sees `pdf-processing`.
2.  **Prompting**: LLM sees "pdf-processing: Extract text/tables..." in system prompt.
3.  **Activation**: LLM calls `read_file("/skills/pdf-processing/SKILL.md")`.
4.  **Execution**: LLM reads instructions, sees it needs to run a script, and calls `execute("python3 /skills/pdf-processing/scripts/extract_forms.py ...")`.

### Backend Protocol Adherence
Our `DockerExecutionBackend` satisfies `deepagents.backends.protocol.SandboxBackendProtocol`:

```python
@runtime_checkable
class SandboxBackendProtocol(BackendProtocol, Protocol):
    def execute(self, command: str) -> ExecuteResponse: ...
    @property
    def id(self) -> str: ...
```

### Backend Composition
The agent uses `CompositeBackend` to route operations:
```python
backend = CompositeBackend(
    default=DockerExecutionBackend(root_dir=WORKSPACE_DIR, ...),
    routes={"/skills/": FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True)}
)
```
*   **Default route** (`DockerExecutionBackend`): Handles workspace files and executes commands in Docker.
*   **`/skills/` route** (`FilesystemBackend`): Read-only access to skills on host.

---

## 5. Safety & Configuration

The agent is configured with Human-in-the-Loop (HITL) safety rails using `deepagents` configuration patterns.

**`interrupt_on` Configuration** (`agent/config.py`):
The agent requires user approval for high-risk operations:
```python
INTERRUPT_ON = {
    "execute": {"allowed_decisions": ["approve", "reject"]},
    "edit_file": {"allowed_decisions": ["approve", "reject"]},
}
```

**Docker Isolation Benefits**:
*   Commands execute in an isolated container, not directly on the host OS.
*   Pre-defined environment with only necessary packages installed.
*   `/workspace` volume mount limits container's write access to a specific directory.
*   Container can be easily reset or rebuilt if compromised.

---

## 6. Project Structure

```
code-execution-deep-agent/
├── libs/                           # Reusable libraries
│   ├── backends/
│   │   └── docker/
│   │       ├── backend.py          # DockerExecutionBackend implementation
│   │       ├── Dockerfile          # Container definition
│   │       └── README.md           # Docker backend documentation
│   └── middleware/
│       └── skills.py               # SkillsMiddleware implementation
├── agent/                          # Agent configuration and entry point
│   ├── config.py                   # Configuration (backends, model, middleware)
│   ├── prompt.py                   # System prompt
│   └── graph.py                    # Agent graph instantiation
├── skills/                         # Skill definitions (read-only)
│   ├── csv-analytics/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── docs/
│   └── pdf-processing/
│       ├── SKILL.md
│       ├── scripts/
│       └── docs/
├── workspace/                      # Agent workspace (mounted into Docker)
│   ├── data/                       # Input data
│   ├── scripts/                    # Agent-generated scripts
│   └── results/                    # Output files
├── tests/                          # Unit and integration tests
├── docs/                           # Documentation
│   ├── architecture.md             # This file
│   └── docker-setup.md             # Docker setup guide
└── langgraph.json                  # LangGraph configuration

```

## 7. Implementation Status

✅ **Completed**:
*   `DockerExecutionBackend` with full Docker integration
*   `SkillsMiddleware` with eager skill discovery
*   Docker container with pre-installed packages and symlink structure
*   `CompositeBackend` routing for workspace and skills
*   HITL approval for `execute` and `edit_file` operations
*   Example skills: `csv-analytics` and `pdf-processing`
*   Comprehensive test suite
*   Complete documentation (README, docker-setup, architecture)

## 8. Why This Architecture?

**Docker-Based Execution**:
*   **Consistent Paths**: `/data`, `/scripts`, `/results` work identically in file operations and executed commands.
*   **Isolation**: Commands run in a sandboxed environment, not directly on host.
*   **Reproducibility**: Pre-installed packages ensure consistent execution environment.
*   **Portability**: Same experience across macOS, Linux, and Windows.

**vs. MCP**:
*   MCP abstracts tools behind a server. Here, we want the agent to "own" the tools as files, allowing it to read, understand, and even *edit* its own scripts if permitted (self-evolution).

**Progressive Disclosure**:
*   Prevents the context window from filling up with tool definitions for 50 skills when only 1 is needed.
*   Agent loads skill details on-demand via `read_file`, keeping token usage low.

**Modular Design**:
*   Clear separation: `libs/` (reusable), `agent/` (configuration), `skills/` (capabilities).
*   Easy to extend with new backends or middleware.
*   Feature-based organization for scalability.

