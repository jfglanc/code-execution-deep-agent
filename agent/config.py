"""Configuration for the Code Execution Deep Agent.

All configurables including paths, timeouts, model settings, and backend creation.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

from deepagents.backends import CompositeBackend, FilesystemBackend

from agent.backend_local_exec import LocalExecutionBackend
from agent.middleware_skills import SkillsMiddleware
from agent.prompt import SYSTEM_PROMPT
from agent.virtualfs import VirtualMount, VirtualPathResolver

# Load environment variables
load_dotenv()

# Get API key (validation happens when agent is used)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
SKILLS_DIR = PROJECT_ROOT / "skills"

# Ensure directories exist
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
for subdir in ("data", "scripts", "results"):
    (WORKSPACE_DIR / subdir).mkdir(parents=True, exist_ok=True)

# Execution settings
DEFAULT_TIMEOUT = 120  # seconds
MAX_OUTPUT_CHARS = 50_000  # characters

# Model settings
MODEL_NAME = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 8000

# Virtual filesystem configuration (used for both file ops and shell commands)
virtual_mounts = [
    VirtualMount(virtual="/", physical=WORKSPACE_DIR),
    VirtualMount(virtual="/data", physical=WORKSPACE_DIR / "data"),
    VirtualMount(virtual="/scripts", physical=WORKSPACE_DIR / "scripts"),
    VirtualMount(virtual="/results", physical=WORKSPACE_DIR / "results"),
    VirtualMount(virtual="/skills", physical=SKILLS_DIR),
]
VIRTUAL_PATH_RESOLVER = VirtualPathResolver(virtual_mounts)

# Create backends
workspace_backend = LocalExecutionBackend(
    root_dir=WORKSPACE_DIR,
    default_timeout=DEFAULT_TIMEOUT,
    max_output_chars=MAX_OUTPUT_CHARS,
    virtual_mode=True,  # Treat paths as virtual (relative to root_dir)
    virtual_resolver=VIRTUAL_PATH_RESOLVER,
)

skills_backend = FilesystemBackend(
    root_dir=SKILLS_DIR,
    virtual_mode=True,
)

backend = CompositeBackend(
    default=workspace_backend,
    routes={"/skills/": skills_backend},
)

# Create model
model = ChatAnthropic(
    model_name=MODEL_NAME,
    max_tokens=MAX_TOKENS,
)

# Discover skills at import time (eager loading for efficiency)
# This runs synchronously during module import, before any async event loop exists
_skills_discovery = SkillsMiddleware(skills_dir=SKILLS_DIR)
DISCOVERED_SKILLS = _skills_discovery.skills

# Create middleware with pre-discovered skills
skills_middleware = SkillsMiddleware(
    skills_dir=SKILLS_DIR,
    discovered_skills=DISCOVERED_SKILLS,
)

# HITL configuration
INTERRUPT_ON = {
    "execute": {
        "allowed_decisions": ["approve", "reject"],
    },
    "edit_file": {
        "allowed_decisions": ["approve", "reject"],
    },
}
