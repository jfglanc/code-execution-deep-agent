"""Unit tests for SkillsMiddleware.

Tests cover:
- Skill discovery from filesystem
- YAML frontmatter parsing
- Invalid skill handling (missing fields, bad YAML)
- Prompt injection without full content
- State management
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from libs.middleware import SkillsMiddleware


class TestSkillsMiddleware:
    """Test suite for SkillsMiddleware skill discovery and prompt injection."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary skills directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def valid_skill(self, temp_skills_dir):
        """Create a valid skill with proper frontmatter."""
        skill_dir = temp_skills_dir / "test-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
---

# Test Skill

This is a test skill with usage instructions.

## Scripts

- script1.py: Does something useful
""")
        return skill_dir

    @pytest.fixture
    def middleware(self, temp_skills_dir):
        """Create a SkillsMiddleware instance."""
        return SkillsMiddleware(skills_dir=temp_skills_dir)

    def test_skill_discovery_finds_valid_skill(self, middleware, valid_skill):
        """Test that middleware discovers valid SKILL.md files."""
        skills = middleware._discover_skills()
        
        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
        assert skills[0]["description"] == "A test skill for unit testing"
        assert "skill_md_path" in skills[0]
        assert "skill_root" in skills[0]

    def test_frontmatter_parsing_valid(self, middleware, valid_skill):
        """Test parsing valid YAML frontmatter."""
        skill_md = valid_skill / "SKILL.md"
        metadata = middleware._parse_skill_frontmatter(skill_md)
        
        assert metadata["name"] == "test-skill"
        assert metadata["description"] == "A test skill for unit testing"

    def test_frontmatter_missing_raises_error(self, middleware, temp_skills_dir):
        """Test that missing frontmatter raises ValueError."""
        skill_dir = temp_skills_dir / "invalid-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Just a regular markdown file\n\nNo frontmatter here.")
        
        with pytest.raises(ValueError, match="No YAML frontmatter"):
            middleware._parse_skill_frontmatter(skill_md)

    def test_frontmatter_missing_name_raises_error(self, middleware, temp_skills_dir):
        """Test that missing 'name' field raises KeyError."""
        skill_dir = temp_skills_dir / "invalid-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Missing name field
---

# Content
""")
        
        with pytest.raises(KeyError, match="name"):
            middleware._parse_skill_frontmatter(skill_md)

    def test_frontmatter_missing_description_raises_error(self, middleware, temp_skills_dir):
        """Test that missing 'description' field raises KeyError."""
        skill_dir = temp_skills_dir / "invalid-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
---

# Content
""")
        
        with pytest.raises(KeyError, match="description"):
            middleware._parse_skill_frontmatter(skill_md)

    def test_invalid_yaml_raises_error(self, middleware, temp_skills_dir):
        """Test that invalid YAML syntax raises ValueError."""
        skill_dir = temp_skills_dir / "invalid-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: [unclosed bracket
---

# Content
""")
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            middleware._parse_skill_frontmatter(skill_md)

    def test_discovery_skips_invalid_skills(self, middleware, temp_skills_dir, valid_skill):
        """Test that discovery continues after encountering invalid skills."""
        # Create an invalid skill
        invalid_dir = temp_skills_dir / "invalid-skill"
        invalid_dir.mkdir()
        invalid_md = invalid_dir / "SKILL.md"
        invalid_md.write_text("# No frontmatter")
        
        # Discovery should find only the valid skill
        skills = middleware._discover_skills()
        
        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"

    def test_discovery_ignores_non_directories(self, middleware, temp_skills_dir):
        """Test that discovery ignores regular files in skills directory."""
        # Create a regular file (not a directory)
        (temp_skills_dir / "README.md").write_text("Not a skill")
        
        skills = middleware._discover_skills()
        
        assert len(skills) == 0

    def test_discovery_ignores_dirs_without_skill_md(self, middleware, temp_skills_dir):
        """Test that directories without SKILL.md are ignored."""
        # Create a directory without SKILL.md
        (temp_skills_dir / "empty-dir").mkdir()
        
        skills = middleware._discover_skills()
        
        assert len(skills) == 0

    def test_prompt_injection_contains_metadata(self, middleware, valid_skill):
        """Test that formatted prompt contains skill metadata."""
        skills = middleware._discover_skills()
        prompt = middleware._format_skills_prompt(skills)
        
        assert "test-skill" in prompt
        assert "A test skill for unit testing" in prompt
        assert "SKILL.md" in prompt

    def test_prompt_injection_does_not_contain_full_content(self, middleware, valid_skill):
        """Test that prompt does NOT contain full skill content."""
        skills = middleware._discover_skills()
        prompt = middleware._format_skills_prompt(skills)
        
        # Should not contain content from the SKILL.md body
        assert "Does something useful" not in prompt
        assert "script1.py" not in prompt

    def test_prompt_contains_progressive_disclosure_instructions(self, middleware, valid_skill):
        """Test that prompt contains instructions for progressive disclosure."""
        skills = middleware._discover_skills()
        prompt = middleware._format_skills_prompt(skills)
        
        assert "progressive" in prompt.lower() or "Progressive" in prompt
        assert "read_file" in prompt
        assert "execute" in prompt

    def test_skills_discovered_at_init(self, temp_skills_dir, valid_skill):
        """Test that skills are discovered during middleware initialization."""
        middleware = SkillsMiddleware(skills_dir=temp_skills_dir)
        
        assert len(middleware.skills) == 1
        assert middleware.skills[0]["name"] == "test-skill"
        assert middleware.skills[0]["description"] == "A test skill for unit testing"

    def test_pre_discovered_skills(self, temp_skills_dir):
        """Test that middleware accepts pre-discovered skills."""
        pre_discovered = [
            {"name": "custom-skill", "description": "Custom", "skill_md_path": "/path/to/skill.md"}
        ]
        
        middleware = SkillsMiddleware(
            skills_dir=temp_skills_dir,
            discovered_skills=pre_discovered
        )
        
        assert middleware.skills == pre_discovered
        assert len(middleware.skills) == 1
        assert middleware.skills[0]["name"] == "custom-skill"

    def test_wrap_model_call_injects_prompt(self, temp_skills_dir, valid_skill):
        """Test that wrap_model_call injects skills prompt into system prompt."""
        # Create middleware (skills discovered at init)
        middleware = SkillsMiddleware(skills_dir=temp_skills_dir)
        
        # Mock request
        request = Mock()
        request.system_prompt = "Original system prompt"
        
        # Mock handler
        handler = Mock(return_value="response")
        
        # Wrap model call
        middleware.wrap_model_call(request, handler)
        
        # Check that override was called with extended prompt
        request.override.assert_called_once()
        call_kwargs = request.override.call_args[1]
        assert "system_prompt" in call_kwargs
        assert "Original system prompt" in call_kwargs["system_prompt"]
        assert "test-skill" in call_kwargs["system_prompt"]

    def test_multiple_skills_discovery(self, middleware, temp_skills_dir):
        """Test discovery of multiple skills."""
        # Create multiple valid skills
        for i in range(3):
            skill_dir = temp_skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"""---
name: skill-{i}
description: Description for skill {i}
---

# Skill {i}
""")
        
        skills = middleware._discover_skills()
        
        assert len(skills) == 3
        names = [s["name"] for s in skills]
        assert "skill-0" in names
        assert "skill-1" in names
        assert "skill-2" in names

    def test_empty_skills_directory(self, middleware):
        """Test behavior with empty skills directory."""
        skills = middleware._discover_skills()
        
        assert len(skills) == 0

    def test_format_prompt_with_no_skills(self, middleware):
        """Test that format_prompt returns empty string with no skills."""
        prompt = middleware._format_skills_prompt([])
        
        assert prompt == ""

