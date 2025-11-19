# Code Execution Deep Agent

A local code-executing deep agent with **Progressive Disclosure Skills**. This agent can execute Python scripts, process data files, and dynamically load specialized capabilities without bloating its context window.

## Features

- **Local Code Execution**: Run shell commands and Python scripts on your machine
- **Progressive Disclosure**: Skills are loaded on-demand, not all at startup
- **File-Based Skills**: Capabilities defined in SKILL.md files with scripts and docs
- **Safety Rails**: Human-in-the-loop approval for command execution and file edits
- **Specialized Skills**:
  - CSV Analytics: Efficiently process large CSV files
  - PDF Processing: Extract form fields and text from PDFs

## Architecture

This project demonstrates:
- Custom `DockerExecutionBackend` for isolated command execution with consistent filesystem paths
- Custom `SkillsMiddleware` for progressive capability disclosure
- Skills-based architecture where tools are files, not hardcoded Python functions
- Docker-based execution environment where `/data`, `/scripts`, `/results` paths work consistently in both file operations and executed scripts

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) - Modern, fast Python package manager
- Docker Desktop installed and running
- Anthropic API key for Claude models

### Installation

1. **Install uv** (if you haven't already):

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. **Clone the repository**:

```bash
git clone https://github.com/jfglanc/code-execution-deep-agent.git
cd code-execution-deep-agent
```

3. **Install dependencies**:

```bash
uv sync --dev
```

This automatically:
- Creates a virtual environment in `.venv/`
- Installs the project in editable mode
- Installs all dependencies including LangGraph CLI
- Generates `uv.lock` for reproducible builds

4. **Set up your API key**:

```bash
cp .env.example .env
```

Then edit `.env` and add your Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Enable LangSmith tracing
LANGSMITH_API_KEY=lsv2...
```

5. **Build the Docker image**:

```bash
docker build -f libs/backends/docker/Dockerfile -t code-execution-agent:latest .
```

This creates a container image with Python 3.11 and pre-installed data science packages (pandas, numpy, matplotlib, etc.).

6. **Start the execution container**:

```bash
docker run -d --name code-execution-agent -v "$(pwd)/workspace:/workspace" code-execution-agent:latest
```

On Windows (PowerShell), use:
```powershell
docker run -d --name code-execution-agent -v "${PWD}/workspace:/workspace" code-execution-agent:latest
```

**Note**: The container must be running for the agent to execute commands. See `docs/docker-setup.md` for troubleshooting and management.

7. **Generate sample data** (optional, for demos):

```bash
uv run python workspace/data/generate_sample_data.py
```

This creates:
- `workspace/data/orders.csv` - 10,000 sample order records
- `workspace/data/sample_form.pdf` - PDF with fillable form fields

8. **Start the LangGraph server**:

```bash
uv run langgraph dev
```

This starts the agent server with:
- Development UI at http://localhost:8123
- API server for agent interactions
- Hot reload on code changes

9. **Open the UI and start chatting**:

Navigate to **http://localhost:8123** in your browser to interact with the agent.

## Usage Examples

### CSV Analysis

```
> What are the top 5 orders by amount in /workspace/data/orders.csv?
```

The agent will:
1. Read the csv-analytics SKILL.md
2. Execute the filter_high_value.py script
3. Return a summary of the top 5 orders

### PDF Form Extraction

```
> Extract the form fields from /workspace/data/sample_form.pdf
```

The agent will:
1. Read the pdf-processing SKILL.md
2. Execute the extract_forms.py script
3. Return the extracted field names and values

### General Queries

The agent can also handle general questions without using skills:

```
> What is the difference between pandas and numpy?
```

## Project Structure

```
libs/
├── backends/
│   └── docker/
│       ├── backend.py       # DockerExecutionBackend implementation
│       ├── Dockerfile       # Container definition
│       └── README.md        # Docker backend documentation
└── middleware/
    └── skills.py            # SkillsMiddleware implementation

agent/
├── config.py                # Configuration and setup
├── prompt.py                # System prompt
└── graph.py                 # Agent graph and main entry point

skills/
├── csv-analytics/
│   ├── SKILL.md            # Skill definition and usage
│   ├── scripts/            # Python scripts for CSV processing
│   └── docs/               # Supporting documentation
└── pdf-processing/
    ├── SKILL.md            # Skill definition and usage
    ├── scripts/            # Python scripts for PDF extraction
    └── docs/               # Supporting documentation

workspace/
└── data/                   # Sample and working data files

tests/
├── test_execute_backend.py      # Unit tests for DockerExecutionBackend
├── test_skills_middleware.py    # Unit tests for SkillsMiddleware
├── test_e2e_csv_flow.py         # End-to-end CSV workflow tests
└── test_e2e_pdf_flow.py         # End-to-end PDF workflow tests
```

## How It Works

### Progressive Disclosure Pattern

Instead of loading all skill documentation into the agent's context at startup, the agent:

1. **Startup**: Sees only skill names and brief descriptions in system prompt
2. **Discovery**: When a query matches a skill, reads the SKILL.md file
3. **Execution**: Follows SKILL.md instructions to run scripts via `execute` tool
4. **Efficiency**: Only loads what's needed, keeping token usage low

### Backend Architecture

The agent uses a `CompositeBackend`:
- **Default**: `DockerExecutionBackend` (workspace/) - read-write + execute in container
- **Route `/skills/`**: `FilesystemBackend` (skills/) - read-only on host

This separation ensures:
- Skills are protected from accidental modification
- Commands execute in isolated Docker environment
- Workspace is fully accessible for data processing
- Clear distinction between capabilities and working data

### Safety Features

The agent requires user approval for:
- **Command execution** (`execute` tool): Review commands before they run
- **File edits** (`edit_file` tool): Preview changes before applying

This prevents accidental destructive operations while maintaining flexibility.

## Running Tests

Run all tests:

```bash
uv run pytest
```

Run specific test suites:

```bash
# Unit tests only
uv run pytest tests/test_execute_backend.py tests/test_skills_middleware.py

# Integration tests (requires ANTHROPIC_API_KEY)
uv run pytest tests/test_e2e_csv_flow.py tests/test_e2e_pdf_flow.py -m integration
```

## Creating Custom Skills

To add a new skill:

1. Create a directory under `skills/`:

```bash
mkdir -p skills/my-skill/scripts skills/my-skill/docs
```

2. Create `SKILL.md` with frontmatter:

```yaml
---
name: my-skill
description: Brief description of what this skill does
---

# My Skill

Detailed usage instructions...

## Scripts

- my_script.py: What it does and how to use it
```

3. Add scripts under `scripts/`:

```python
#!/usr/bin/env python3
# Your script here
```

4. Add supporting docs under `docs/` (optional)

The agent will automatically discover and use your skill!

## Technical Details

For detailed architecture information, see [`docs/architecture.md`](docs/architecture.md).

## License

MIT License - See LICENSE file for details

---

By Jan Franco Glanc Gomez
