"""Agent Skills, independent of where they're kept: the SkillLibrary port (core layer: plain types and a Protocol).

A skill (agentskills.io) is a folder with a SKILL.md: a short name and description, which say what it's for and when to
use it, then instructions, and perhaps reference files. They're shown to the model a level at a time (progressive
disclosure, D208): every skill's name and description are always in the system prompt; a skill's SKILL.md only when the
model asks for it (load_skill); a reference file only when the skill says it's needed. The composition root builds the
adapter (infrastructure/skills.py, the skills/ folder) and passes it in; the assistant uses only this port.

Skills are SpendWise's own text, kept in its repository: trusted instructions, unlike a tool's result or a receipt.
A skill's scripts are run by the server (run_script), never by the model, and their code never reaches it (D209).
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


class SkillNotFoundError(LookupError):
    """No skill by that name, or no such file in it."""


class SkillScriptError(RuntimeError):
    """A skill's script failed: it couldn't be started, ran too long, exited with an error, or didn't answer JSON.
    Its message is for the log."""


@dataclass(frozen=True)
class SkillSummary:
    """What the model always sees of a skill: its name, its description (what it does, and when to use it), and the
    files it may also be asked for (paths relative to the skill's folder, e.g. "references/merchants.md")."""

    name: str
    description: str
    files: tuple[str, ...] = field(default_factory=tuple)


class SkillLibrary(Protocol):
    """The skills the assistant may use."""

    def catalog(self) -> list[SkillSummary]:
        """Every valid skill, by name."""
        ...

    def read(self, name: str, file: str | None = None) -> str:
        """A skill's instructions (its SKILL.md, without the frontmatter), or one of its listed files. Raises
        SkillNotFoundError for an unknown skill or a file it doesn't list."""
        ...

    def run_script(self, name: str, script: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run one of a skill's scripts (e.g. "scripts/compute_report.py") with `payload` as its JSON input, and
        return its JSON output. Raises SkillNotFoundError for a script the skill doesn't have, SkillScriptError if it
        fails."""
        ...
