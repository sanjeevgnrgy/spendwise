"""Agent Skills in the assistant: SkillTool (skill_tool.py), the catalog in the instruction and the load_skill tool.

Inside the assistant, beside tools/ and delegation/ (application/ imports it; it imports agent/ for the events and call
handlers, never application/ or api/). The skills themselves come through core/skills.SkillLibrary (D208).
"""

from app.modules.assistant.skills.skill_tool import LOAD_SKILL, SkillTool

__all__ = ["LOAD_SKILL", "SkillTool"]
