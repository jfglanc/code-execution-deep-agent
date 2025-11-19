"""Skills middleware for progressive disclosure of agent capabilities.

This module provides SkillsMiddleware which discovers skill definitions from
the filesystem, parses their metadata, and injects a progressive-disclosure
prompt into the system that instructs the agent to load skills on-demand.

Skills are discovered at initialization time (typically at import/startup),
not during agent execution, for better performance and simpler async handling.
"""

import re
from collections.abc import Awaitable, Callable
from pathlib import Path

import yaml
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)


class SkillsMiddleware(AgentMiddleware):
    """Middleware that implements progressive disclosure for agent skills.

    This middleware injects a system prompt that lists available skills
    (name and description only) without loading full SKILL.md content.
    
    Skills are discovered at initialization time for efficiency. The agent
    is instructed to use read_file() to load specific SKILL.md files only
    when relevant to the user's request.
    """

    def __init__(self, skills_dir: Path | str, discovered_skills: list[dict] | None = None) -> None:
        """Initialize the SkillsMiddleware.

        Args:
            skills_dir: Path to directory containing skill subdirectories.
                       Used for discovery if discovered_skills not provided.
            discovered_skills: Pre-discovered skill metadata. If provided,
                             skips filesystem scanning for efficiency.
        """
        self.skills_dir = Path(skills_dir)
        
        # Use pre-discovered skills if provided, otherwise discover now
        if discovered_skills is not None:
            self.skills = discovered_skills
        else:
            self.skills = self._discover_skills()


    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject skills prompt into system prompt before model call.

        Args:
            request: Model request to modify.
            handler: Handler to call with modified request.

        Returns:
            Model response from handler.
        """
        if self.skills:
            skills_prompt = self._format_skills_prompt(self.skills)
            
            # Append to existing system prompt
            if request.system_prompt:
                request = request.override(
                    system_prompt=request.system_prompt + "\n\n" + skills_prompt
                )
            else:
                request = request.override(system_prompt=skills_prompt)

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Async version of wrap_model_call."""
        if self.skills:
            skills_prompt = self._format_skills_prompt(self.skills)
            
            if request.system_prompt:
                request = request.override(
                    system_prompt=request.system_prompt + "\n\n" + skills_prompt
                )
            else:
                request = request.override(system_prompt=skills_prompt)

        return await handler(request)

    def _discover_skills(self) -> list[dict]:
        """Scan skills directory for SKILL.md files and parse metadata.

        Returns:
            List of skill metadata dicts with keys:
            - name: Skill name from frontmatter
            - description: Skill description from frontmatter
            - skill_root: Absolute path to skill directory
            - skill_md_path: Absolute path to SKILL.md file
        """
        skills = []

        if not self.skills_dir.exists():
            return skills

        # Scan for subdirectories containing SKILL.md
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                metadata = self._parse_skill_frontmatter(skill_md)
                metadata["skill_root"] = str(skill_dir.resolve())
                metadata["skill_md_path"] = str(skill_md.resolve())
                metadata["virtual_skill_md_path"] = f"/skills/{skill_dir.name}/SKILL.md"
                skills.append(metadata)
            except (ValueError, KeyError) as e:
                # Skip invalid skills but log the error
                print(f"Warning: Skipping invalid skill {skill_dir.name}: {e}")
                continue

        return skills

    def _parse_skill_frontmatter(self, skill_md_path: Path) -> dict:
        """Parse YAML frontmatter from a SKILL.md file.

        Args:
            skill_md_path: Path to SKILL.md file.

        Returns:
            Dict with 'name' and 'description' from frontmatter.

        Raises:
            ValueError: If frontmatter is missing or invalid.
            KeyError: If required fields (name, description) are missing.
        """
        content = skill_md_path.read_text()

        # Extract YAML frontmatter between --- delimiters
        # Pattern: starts with ---, captures content until next ---
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)

        if not match:
            raise ValueError(f"No YAML frontmatter found in {skill_md_path}")

        yaml_content = match.group(1)

        try:
            metadata = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in frontmatter: {e}") from e

        if not isinstance(metadata, dict):
            raise ValueError("Frontmatter must be a YAML dictionary")

        # Validate required fields
        if "name" not in metadata:
            raise KeyError("Missing required field 'name' in frontmatter")
        if "description" not in metadata:
            raise KeyError("Missing required field 'description' in frontmatter")

        return {
            "name": metadata["name"],
            "description": metadata["description"],
        }

    def _format_skills_prompt(self, skills: list[dict]) -> str:
        """Format the skills section of the system prompt.

        This creates a prompt that:
        1. Explains progressive disclosure pattern
        2. Lists available skills with name and description
        3. Instructs agent to use read_file() to load SKILL.md when needed

        Args:
            skills: List of skill metadata dicts.

        Returns:
            Formatted prompt string to inject into system prompt.
        """
        if not skills:
            return ""

        # Build the skill list
        skill_items = []
        for skill in skills:
            virtual_path = skill.get("virtual_skill_md_path", skill["skill_md_path"])
            skill_items.append(
                f"- **{skill['name']}**: {skill['description']}\n"
                f"  Path: `{virtual_path}`"
            )

        skills_list = "\n".join(skill_items)

        prompt = f"""## Available Skills (Progressive Disclosure)

You have access to the following skills. Each skill provides specialized capabilities
through scripts and documentation.

**IMPORTANT - Progressive Disclosure Pattern:**
1. The skill list below shows ONLY high-level metadata (name + description)
2. Do NOT load all skill details at startup - this wastes tokens
3. When a user request matches a skill's description, use `read_file()` to load that
   skill's SKILL.md file to see detailed usage instructions
4. The SKILL.md will reference scripts (under `scripts/`) and docs (under `docs/`)
5. Use the `execute` tool to run scripts when instructed by SKILL.md
6. Only load additional docs (from `docs/`) if explicitly referenced and needed

### Skill Catalog

{skills_list}

### Usage Guidelines

- **Read SKILL.md only when relevant**: Don't load all skills preemptively
- **Follow SKILL.md instructions**: Each skill explains how to use its scripts
- **Use execute for scripts**: Run scripts via `execute("python3 /path/to/script.py ...")`
- **Prefer off-model processing**: When data is large (>1000 rows), use scripts to
  filter/process data rather than loading it all into context

### Example Workflow

1. User asks: "Find top 5 orders in my CSV"
2. You identify: csv-analytics skill is relevant
3. You call: `read_file("/skills/csv-analytics/SKILL.md")`
4. You learn: There's a filter_high_value.py script
5. You call: `execute("python3 /skills/csv-analytics/scripts/filter_high_value.py ...")`
6. You summarize: The filtered results for the user
"""

        return prompt

