# Code Execution Deep Agent

A deep research agent with code execution capabilities built using LangGraph and Deep Agents.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) - Modern, fast Python package manager
- API keys for:
  - **Anthropic** (Claude models) - [Get API key](https://console.anthropic.com/)
  - **OpenAI** (GPT models) - [Get API key](https://platform.openai.com/)
  - **Tavily** (web search) - [Get API key](https://tavily.com/)

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

4. **Set up your API keys**:

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Optional: Enable LangSmith tracing
LANGSMITH_API_KEY=lsv2...
```

5. **Start the LangGraph server**:

```bash
uv run langgraph dev
```

6. **Open the UI** and start chatting:

```
http://localhost:8123
```

---

By Jan Franco Glanc Gomez - Open Source
