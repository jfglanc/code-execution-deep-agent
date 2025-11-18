"""
Configuration for Deep Research Agent system.

All models, limits, and behavioral parameters are defined here.
"""

from langchain.chat_models import init_chat_model


# ===== ADVISOR CONFIGURATION =====
# We are choosing Claude for a warm and friendly tone.
# Temperature is high to make the advisor more divergent and exploratory with the user.
ADVISOR_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.8
}

def get_advisor_model():
    """Get initialized advisor model."""
    return init_chat_model(
        model=ADVISOR_CONFIG["model"],
        temperature=ADVISOR_CONFIG["temperature"]
    )


# ===== RESEARCH SUPERVISOR CONFIGURATION =====
RESEARCH_SUPERVISOR_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0
}

def get_supervisor_model():
    """Get initialized supervisor model."""
    return init_chat_model(
        model=RESEARCH_SUPERVISOR_CONFIG["model"],
        temperature=RESEARCH_SUPERVISOR_CONFIG["temperature"]
    )


# ===== RESEARCH SUBAGENT CONFIGURATION =====
# Choosing GPT-5-mini to save costs on token-heavy tasks. 
# Temperature is 0 to avoid hallucinations.
RESEARCH_SUBAGENT_CONFIG = {
    "model": "gpt-5-mini",
    "temperature": 0
}

def get_researcher_model():
    """Get initialized researcher model."""
    return init_chat_model(
        model=RESEARCH_SUBAGENT_CONFIG["model"],
        temperature=RESEARCH_SUBAGENT_CONFIG["temperature"]
    )


# ===== REPORT WRITER CONFIGURATION =====
# Choosing Claude for a warm, natural output.
# Temperature is 0 to avoid hallucinations.
REPORT_WRITER_CONFIG = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0,
    "max_tokens": 6000 # Modify for longer reports
}

def get_report_writer_model():
    """Get initialized report writer model."""
    return init_chat_model(
        model=REPORT_WRITER_CONFIG["model"],
        temperature=REPORT_WRITER_CONFIG["temperature"],
        max_tokens=REPORT_WRITER_CONFIG["max_tokens"]
    )


# ===== RESEARCH BEHAVIORAL LIMITS =====
# These parameters heavily affect cost of research and latency!!!
RESEARCH_LIMITS = {
    "max_subagents": 5,              # Max concurrent subagents supervisor can spawn
    "max_supervisor_iterations": 6,  # Max task() calls supervisor can make
    "max_researcher_searches": 3     # Max searches each researcher should perform
}


# ===== TAVILY SEARCH CONFIGURATION =====

TAVILY_CONFIG = {
    "max_results": 3,              # Results per search
    "topic": "general",            # general, news, or finance
    "include_raw_content": False   # Don't include full webpage HTML
}


# ===== FILE PATH CONSTANTS =====
# These are used to coordinate research between the supervisor and the researcher subagents.
RESEARCH_INDEX_PATH = "/research/index.md"
RESEARCH_BASE_DIR = "/research"

