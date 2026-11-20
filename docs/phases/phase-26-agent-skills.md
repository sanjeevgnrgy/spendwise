# Phase 26: Agent Skills

**Goal:** the assistant learns how to do particular tasks from **skills**: folders of instructions, in the open Agent
Skills format, that it reads only when a task calls for them. Part 1: the categorization skill. Part 2: a monthly
report, worked out by a script the server runs, shown as a card with downloads. On both branches (`main` and
`multi-server`). Decisions: D208 (Part 1).

**The owner's choices** (asked before building): two parts; the server, not the model, runs a skill's script; the
report's markdown is a download (the chat stays plain text); up to 4 live Gemini calls.

## The ideas

**Progressive disclosure.** A skill is shown to the model a level at a time:

1. **Always:** its name and a one-line description that says what it's for and when to use it, in the system
   instruction ("categorization: Chooses the right SpendWise category… Use when recording or changing an expense and
   the user didn't name the category").
2. **When a task matches:** the whole SKILL.md: steps, rules, examples. The model asks for it with `load_skill`.
3. **When the skill says so:** a file beside it (the merchant list), with `load_skill(name, file)`.

Like a new colleague's desk: the shelf shows every manual's spine, so they know what exists; they open the one they
need; and they only pull a table from the appendix when the manual says to.

**Why skills keep the prompt small.** Everything in the system instruction is sent, and paid for, on every step of every
turn, whether or not it's used. Putting every rule for every task there makes each request longer, slower and dearer,
and buries the rule that matters among those that don't. With skills, the always-on cost is a few lines per skill
(313 characters for categorization), and the full 3,815 characters arrive only on turns that need them. Adding a skill
adds a line, not a page.

**Instructions, not data.** Everything else a tool returns is data, never to be obeyed (a merchant called "ignore your
rules" changes nothing). A skill is the app's own text, from its repository, so `load_skill`'s result is the one
exception, and the instruction says so. That's also why skills come only from `skills/`, never from a person.

## Part 1: the skills, the catalog, load_skill, categorization

| Where | What |
|---|---|
| `skills/categorization/SKILL.md`, `references/merchants.md` | the skill: categories, steps, rules; the merchant list |
| `backend/app/core/skills.py` | the `SkillLibrary` port |
| `backend/app/infrastructure/skills.py` | `FolderSkillLibrary`: reads the folder once, checks the format, lists readable files |
| `backend/app/modules/assistant/skills/skill_tool.py` | `SkillTool`: the catalog in the instruction, `load_skill`, its handler |
| agent loop | `Agent(extensions=...)`: the delegator and the skills, each with tools, handlers and rules |
| bootstrap, settings, chips | `SKILLS_DIR`, `build(skills=...)`, "Reading a skill…" (English, Hindi) |

**How it was checked:** 16 offline checks (D208), every earlier suite, and 2 live calls: Gemini read the categorization
skill on its own for a Rapido ride and filed it under Transport.

### Try it

```powershell
.\run.ps1                 # the skills are read from skills/ at the first message
cd web; npm run dev
```

In the chat: "Add 250 for a Rapido ride to office today, paid by UPI". The chips show "Reading a skill…" then "Saving
expense…", and the expense is filed under Transport. To add a skill: a new folder in `skills/` with a SKILL.md, then
restart the backend.
