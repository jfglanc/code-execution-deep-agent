"""Utilities for working with the agent's virtual filesystem abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import bashlex


@dataclass(frozen=True)
class VirtualMount:
    """Mapping between a virtual path prefix and its physical location."""

    virtual: str
    physical: Path


class VirtualPathResolver:
    """Resolves virtual paths (e.g., /skills/...) to physical filesystem paths.

    This resolver lets the agent use clean, absolute-looking paths everywhere:

        /skills/...    -> maps to the project's skills directory
        /data/...      -> maps to workspace/data
        /results/...   -> maps to workspace/results
        /...           -> maps to the workspace root

    File operations already understand these virtual paths through the backend
    routing logic. Shell commands, however, require explicit rewriting so that
    subprocesses receive real filesystem paths. This resolver keeps the agent's
    experience consistent by transparently rewriting shell commands before they
    are executed.
    """

    def __init__(self, mounts: Iterable[VirtualMount]):
        normalized = {
            self._normalize_prefix(m.virtual): Path(m.physical).resolve()
            for m in mounts
        }

        if "/" not in normalized:
            raise ValueError("VirtualPathResolver requires a '/' mount for workspace root")

        # Sort by descending prefix length so that /skills takes precedence over /
        self._mounts: list[tuple[str, Path]] = sorted(
            normalized.items(), key=lambda item: len(item[0]), reverse=True
        )

    def rewrite_command(self, command: str) -> str:
        """Rewrite a shell command so virtual paths become real filesystem paths."""
        try:
            trees = bashlex.parse(command)
        except bashlex.errors.ParsingError:
            # If the command can't be parsed, fall back to the original string.
            return command

        replacements: list[tuple[int, int, str]] = []

        def visit(node):
            if getattr(node, "kind", "") == "word" and getattr(node, "word", ""):
                new_word = self._rewrite_word(node.word)
                if new_word != node.word:
                    replacements.append((node.pos[0], node.pos[1], new_word))
            for child in getattr(node, "parts", []) or []:
                visit(child)

        for tree in trees:
            visit(tree)

        if not replacements:
            return command

        replacements.sort(key=lambda item: item[0])
        rebuilt: list[str] = []
        last_index = 0

        for start, end, value in replacements:
            rebuilt.append(command[last_index:start])
            rebuilt.append(value)
            last_index = end

        rebuilt.append(command[last_index:])
        return "".join(rebuilt)

    def _rewrite_word(self, word: str) -> str:
        """Rewrite a single shell word, preserving surrounding quotes."""
        if not word:
            return word

        quote = word[0]
        if quote in {"'", '"'} and len(word) >= 2 and word[-1] == quote:
            inner = word[1:-1]
            rewritten = self._rewrite_unquoted(inner)
            if rewritten != inner:
                return f"{quote}{rewritten}{quote}"
            return word

        return self._rewrite_unquoted(word)

    def _rewrite_unquoted(self, token: str) -> str:
        """Rewrite an unquoted token that may contain a virtual path."""
        if not token:
            return token

        rebased = self._rebase_token(token)
        if rebased is not None:
            return rebased

        # Handle common assignment patterns like flag=/data/file.csv
        for separator in ("=", ":"):
            if separator in token:
                head, tail = token.split(separator, 1)
                rewritten_tail = self._rebase_token(tail)
                if rewritten_tail is not None:
                    return separator.join([head, rewritten_tail])

        return token

    def _rebase_token(self, value: str) -> str | None:
        """Rebase a token that starts with a virtual prefix."""
        if not value.startswith("/"):
            return None

        for prefix, physical in self._mounts:
            if prefix == "/":
                suffix = value[1:]
                return str(physical if not suffix else physical / suffix)

            if value == prefix or value.startswith(prefix + "/"):
                suffix = value[len(prefix) :].lstrip("/")
                return str(physical if not suffix else physical / suffix)

        return None

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        if prefix != "/":
            prefix = prefix.rstrip("/")
        return prefix

