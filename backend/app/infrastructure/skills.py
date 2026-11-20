"""The SkillLibrary port over a folder: FolderSkillLibrary reads skills/<name>/SKILL.md and the files beside it.

Infrastructure: the only code that reads skills from disk. The composition root builds it on SKILLS_DIR (the project's
skills/ folder) and passes it in. It reads the folder once, on first use, and keeps what it found (restart to pick up
an edited skill). A skill is kept only if it follows the format (agentskills.io/specification, D208):

- frontmatter between "---" lines with `name` (1-64 characters: lowercase letters, digits and single hyphens, not at
  either end, the same as the folder's name) and `description` (1-1024 characters); other fields are ignored. Only
  simple "key: value" lines are read (no YAML library is installed for this): enough for these two fields;
- a body (the instructions) and its files under references/ and assets/, each at most MAX_FILE_BYTES. scripts/ are
  never read out: the server runs them (run_script, D209), the model doesn't see their code.

A script runs in a child process of this Python (`-I`: isolated, no user site, no current folder on the path), from
the skill's folder, with its JSON input on stdin and a time limit (SCRIPT_TIMEOUT_SECONDS); its stdout must be one
JSON object (at most MAX_SCRIPT_OUTPUT bytes). No shell is involved, and only scripts listed when the folder was read
can run.

A file can only be read if it was listed when the folder was read: a name the model sends is looked up, never joined
to a path, so nothing outside a skill's folder can be reached.
"""

import json
import logging
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.skills import SkillNotFoundError, SkillScriptError, SkillSummary

logger = logging.getLogger(__name__)

SKILL_FILE = "SKILL.md"
READABLE_FOLDERS = ("references", "assets")
SCRIPTS_FOLDER = "scripts"
SCRIPT_SUFFIX = ".py"
SCRIPT_TIMEOUT_SECONDS = 10
MAX_SCRIPT_OUTPUT = 1024 * 1024
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_FILE_BYTES = 64 * 1024
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
FIELD = re.compile(r"^([A-Za-z_-]+):\s*(.*)$")


@dataclass(frozen=True)
class _Skill:
    summary: SkillSummary
    body: str
    folder: Path
    scripts: tuple[str, ...]


class FolderSkillLibrary:
    """SkillLibrary over a folder of skills (`root`), read once."""

    def __init__(self, root: Path) -> None:
        """Remember the folder; nothing is read until the catalog is first asked for."""
        self._root = root
        self._skills: dict[str, _Skill] | None = None
        self._lock = threading.Lock()

    def catalog(self) -> list[SkillSummary]:
        """Every valid skill, by name."""
        return [skill.summary for _, skill in sorted(self._loaded().items())]

    def read(self, name: str, file: str | None = None) -> str:
        """The skill's instructions, or one of its listed files. Raises SkillNotFoundError otherwise."""
        skill = self._loaded().get(name)
        if skill is None or (file is not None and file not in skill.summary.files):
            raise SkillNotFoundError(f"{name}/{file or SKILL_FILE}")
        return skill.body if file is None else (skill.folder / file).read_text(encoding="utf-8")

    def run_script(self, name: str, script: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run one of the skill's listed Python scripts with `payload` on stdin; return its JSON output. Raises
        SkillNotFoundError for an unlisted script, SkillScriptError if it fails, times out or answers no JSON
        object."""
        skill = self._loaded().get(name)
        if skill is None or script not in skill.scripts:
            raise SkillNotFoundError(f"{name}/{script}")
        try:
            finished = subprocess.run(
                [sys.executable, "-I", str(skill.folder / script)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=skill.folder,
                timeout=SCRIPT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SkillScriptError(f"{name}/{script}: {exc!r}") from exc
        if finished.returncode != 0 or len(finished.stdout) > MAX_SCRIPT_OUTPUT:
            raise SkillScriptError(f"{name}/{script} exited {finished.returncode}: {finished.stderr[-500:]}")
        try:
            output = json.loads(finished.stdout)
        except json.JSONDecodeError as exc:
            raise SkillScriptError(f"{name}/{script} answered no JSON") from exc
        if not isinstance(output, dict):
            raise SkillScriptError(f"{name}/{script} answered no JSON object")
        return output

    def _loaded(self) -> dict[str, _Skill]:
        """The skills, read from the folder the first time."""
        with self._lock:
            if self._skills is None:
                folders = sorted(self._root.iterdir()) if self._root.is_dir() else []
                found = [_read_skill(folder) for folder in folders if (folder / SKILL_FILE).is_file()]
                self._skills = {skill.summary.name: skill for skill in found if skill is not None}
                logger.info("skills: %s", sorted(self._skills))
            return self._skills


def _read_skill(folder: Path) -> _Skill | None:
    """The skill in `folder`, or None (with a warning saying why) if it doesn't follow the format."""
    match = FRONTMATTER.match((folder / SKILL_FILE).read_text(encoding="utf-8"))
    if match is None:
        logger.warning("skill %s skipped: no frontmatter", folder.name)
        return None
    fields = dict(m.groups() for line in match.group(1).splitlines() if (m := FIELD.match(line.strip())))
    name, description = _unquoted(fields.get("name", "")), _unquoted(fields.get("description", ""))
    if not (len(name) <= MAX_NAME and NAME_PATTERN.match(name) and name == folder.name):
        logger.warning(
            "skill %s skipped: its name must be the folder's, in lowercase letters, digits and hyphens", folder.name
        )
        return None
    if not 0 < len(description) <= MAX_DESCRIPTION:
        logger.warning("skill %s skipped: its description must be 1 to %d characters", name, MAX_DESCRIPTION)
        return None
    files = tuple(sorted(_readable_files(folder)))
    scripts_folder = folder / SCRIPTS_FOLDER
    scripts = tuple(
        sorted(p.relative_to(folder).as_posix() for p in scripts_folder.glob(f"*{SCRIPT_SUFFIX}") if p.is_file())
        if scripts_folder.is_dir()
        else ()
    )
    return _Skill(SkillSummary(name, description, files), match.group(2).strip(), folder, scripts)


def _readable_files(folder: Path) -> list[str]:
    """The skill's files the model may read: those under references/ and assets/, small enough, as relative paths."""
    files = []
    for sub in READABLE_FOLDERS:
        for path in (folder / sub).rglob("*") if (folder / sub).is_dir() else []:
            if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES:
                files.append(path.relative_to(folder).as_posix())
    return files


def _unquoted(value: str) -> str:
    """A frontmatter value without surrounding quotes."""
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value
