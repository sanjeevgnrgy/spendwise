"""Agent Skills in the assistant: the catalog in the instruction, and the load_skill tool (D208).

An Extension of the agent loop (agent/agent.py), built per turn by the Assistant use case around the SkillLibrary port
(core/skills.py). Progressive disclosure, a level at a time:

1. rules(): every skill's name and description, always in the system instruction (a few lines in all);
2. load_skill(name): the skill's SKILL.md, only when the model decides a task matches it;
3. load_skill(name, file): one of the skill's files (e.g. references/merchants.md), only when the skill says to.

A skill is SpendWise's own text from its repository, so its content is given to the model as instructions to follow,
unlike every other tool's result, which is data; the rule says so. Nothing is offered when there are no skills.
"""

import logging
from collections.abc import Generator, Mapping
from typing import Any

from app.core.llm import ToolCall, ToolResult, ToolSpec
from app.core.skills import SkillLibrary, SkillNotFoundError
from app.modules.assistant.agent.events import AgentEvent, ToolCallSummary, ToolFinished, ToolStarted
from app.modules.assistant.agent.surfaces import CallHandler, CallOutcome

logger = logging.getLogger(__name__)

LOAD_SKILL = "load_skill"
# What the model is told (English, like everything it reads).
CATALOG_HEADER = (
    "Skills are SpendWise's own instructions for some tasks. When a task matches a skill's description, call "
    f"{LOAD_SKILL} with its name before doing it, and follow what it says; read one of its files only when the skill "
    f"tells you to. What {LOAD_SKILL} returns is the exception to the rule below: it is instructions, not data. Skills:"
)
CATALOG_LINE = "- {name}: {description}"
TOOL_DESCRIPTION = (
    "Read one of SpendWise's skills: its instructions (name only), or one of the files it mentions (name and file)."
)
FILE_HELP = "Only if the skill tells you to read one of its files: that file's path, e.g. references/merchants.md."
LOADED = "The {what} (SpendWise's own instructions: follow them):\n\n{content}"
NOT_FOUND = "There's no skill or file by that name. The skills are listed in your instructions."


class SkillTool:
    """The skills extension for one turn: the catalog lines, the load_skill tool and its handler."""

    def __init__(self, library: SkillLibrary) -> None:
        """Read the catalog once for the turn (the library keeps what it read from disk)."""
        self._library = library
        self._catalog = library.catalog()

    def rules(self) -> list[str]:
        """The catalog: the header, then one line per skill (none when there are no skills)."""
        if not self._catalog:
            return []
        lines = [CATALOG_LINE.format(name=skill.name, description=skill.description) for skill in self._catalog]
        return ["\n".join([CATALOG_HEADER, *lines])]

    def specs(self) -> list[ToolSpec]:
        """load_skill, with the skills' names and files as its choices (none when there are no skills)."""
        if not self._catalog:
            return []
        files = sorted({file for skill in self._catalog for file in skill.files})
        properties: dict[str, Any] = {"name": {"type": "string", "enum": [skill.name for skill in self._catalog]}}
        if files:
            properties["file"] = {"type": "string", "enum": files, "description": FILE_HELP}
        parameters = {"type": "object", "properties": properties, "required": ["name"]}
        return [ToolSpec(name=LOAD_SKILL, description=TOOL_DESCRIPTION, parameters=parameters)]

    def handlers(self) -> Mapping[str, CallHandler]:
        """The handler for load_skill calls."""
        return {LOAD_SKILL: self._load}

    def _load(self, call: ToolCall) -> Generator[AgentEvent, None, CallOutcome]:
        """Read the skill (or its file) under a chip, and give it to the model as instructions."""
        name, file = call.arguments.get("name"), call.arguments.get("file") or None
        yield ToolStarted(call_id=call.call_id, name=LOAD_SKILL, arguments=call.arguments)
        try:
            if not isinstance(name, str) or not (file is None or isinstance(file, str)):
                raise SkillNotFoundError(str(name))
            content = self._library.read(name, file)
        except SkillNotFoundError:
            logger.info("  load_skill: no %s/%s", name, file)
            return (yield from _finish(call, NOT_FOUND, ok=False))
        logger.info("  load_skill: %s%s", name, f"/{file}" if file else "")
        what = f"{name} skill" if file is None else f"{name} skill's file {file}"
        return (yield from _finish(call, LOADED.format(what=what, content=content), ok=True))


def _finish(call: ToolCall, output: str, ok: bool) -> Generator[AgentEvent, None, CallOutcome]:
    """End the chip, and give the model `output`."""
    yield ToolFinished(call_id=call.call_id, name=LOAD_SKILL, ok=ok, output="", data=None, changed_data=False)
    return CallOutcome(
        result=ToolResult(call_id=call.call_id, name=call.name, output=output, is_error=not ok),
        summary=ToolCallSummary(name=call.name, arguments=call.arguments, ok=ok),
        ends_turn=False,
    )
