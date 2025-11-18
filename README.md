# Code Execution Deep Agent

An open deep research agent that works like a university advisor - helping you discover what you want to learn through conversation, then conducting comprehensive research to deliver a detailed report.

Unlike typical deep research agents that require well-defined research questions, this system guides you from curiosity to comprehensive understanding through natural dialogue. It then uses that context to perfom a comprehensive research by using deep agents and subgraphs.

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

That's it! Start a conversation about what you're curious about.

## How It Works

The system uses three specialized AI agents working together:

### 1. **Advisor Agent** - ReAct Loop
- Helps you explore and refine what you want to research through conversation
- Asks thoughtful questions to understand your interests and curiosity
- Can search the web to help clarify unfamiliar or current topics
- Once you're ready, launches the deep research process

Think of it as chatting with a friendly colleague who helps you figure out what you really want to know.

### 2. **Researcher** - Deep Agent
- Coordinates multiple specialized research agents working in parallel
- Each agent focuses on a distinct aspect of your topic (e.g., for "React vs Vue", one agent researches React, another researches Vue)
- Searches the web, collects sources, and organizes findings into structured markdown files
- Saves raw search results for traceability and comprehensive findings for synthesis

Like a researcher going to the library, systematically gathering materials, taking detailed notes, and organizing everything by topic - but NOT writing the final paper yet.

### 3. **Report Writer** - Deep Agent
- Reads all the organized research findings from the file system passed from the researcher
- Finds connections, patterns, and themes across sources
- Synthesizes everything into one comprehensive, well-written report
- Preserves all citations and creates a cohesive narrative with natural flow

Like sitting down with all your organized notes and sources to write the actual research paper, finding connections and creating a compelling narrative.

**Key Design Philosophy**: Separating research (information gathering) from synthesis (report writing) allows each agent to specialize in what it does best.


## Architecture

Built on [LangGraph](https://langchain-ai.github.io/langgraph/) and [LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview).

### System Flow

```
User Question → Advisor (conversation) → Research Supervisor → Report Writer → Comprehensive Report
                    ↓                           ↓                      ↓
                Refines scope          Spawns research agents    Synthesizes findings
                                      (parallel execution)
```

### Component Overview

**Advisor** ([`src/advisor/`](src/advisor/)):
- ReAct agent with web search capability
- Conversational interface for scope refinement
- Launches research when user confirms

**Research Supervisor** ([`src/researcher/`](src/researcher/)):
- Deep Agent that coordinates parallel research
- Spawns specialized subagents
- Each subagent researches distinct subtopic
- Organizes findings in virtual filesystem (`/research/` directory structure)
- Maintains incremental research index

**Report Writer** ([`src/report_writer/`](src/report_writer/)):
- Deep Agent that synthesizes research findings
- Reads from virtual filesystem
- Creates comprehensive prose-heavy reports (typically 5,000-15,000 words)
- Preserves all citations with proper formatting

### State Management

**Virtual Filesystem** (`state["files"]`):
- Researchers save findings to `/research/[subtopic]/findings.md`
- Raw search results preserved in `/research/[subtopic]/search_N_raw.md`
- Sources organized in `/research/[subtopic]/sources.json`
- Supervisor maintains `/research/index.md` with overview

This approach prevents context window bloat while preserving all research materials for synthesis.

**Main Graph** ([`src/main_graph.py`](src/main_graph.py)):
The orchestrator that wires all three agents together with conditional routing based on user approval.

## Configuration

Customize models, limits, and behavior in [`src/config.py`](src/config.py):

### Models
- **Advisor**: Claude Sonnet 4.5 (conversational, creative)
- **Research Supervisor**: Claude Sonnet 4.5 (coordination, planning)
- **Research Subagents**: GPT-5-mini (cost-effective for parallel execution)
- **Report Writer**: Claude Sonnet 4.5 (high-quality synthesis)

### Research Limits
- Max 3 parallel research agents (prevents overwhelming API)
- Max 6 supervisor iterations (prevents runaway delegation)
- Max 5 searches per researcher (focused, efficient research)

### Tavily Search
- 3 results per search query
- General topic mode (vs news or finance)
- Snippet-based (not full webpage content)


### Project Structure

```
src/
├── advisor/          # Conversational advisor agent
├── researcher/       # Deep Agent supervisor + research subagents
├── report_writer/    # Deep Agent report synthesis
├── shared/           # Shared utilities
├── config.py         # Centralized configuration
├── state.py          # Graph state schema
└── main_graph.py     # Main orchestration graph
```

By Jan Franco Glanc Gomez - Open Source
