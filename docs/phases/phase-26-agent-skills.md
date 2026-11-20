# Phase 26: Agent Skills

**Goal:** the assistant learns how to do particular tasks from **skills**: folders of instructions, in the open Agent
Skills format, that it reads only when a task calls for them. Part 1: the categorization skill. Part 2: a monthly
report, worked out by a script the server runs, shown as a card with downloads. On both branches (`main` and
`multi-server`). Decisions: D208 (Part 1), D209 (Part 2).

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

## Part 2: the monthly report, a script the server runs, a card with downloads

"Give me my monthly report for November" now gets a report card, and two buttons to save the report.

**How a report is made.**

1. The model sees the `monthly-report` skill in the catalog and reads it (`load_skill`): when to use it, the steps,
   what the reply says, the tone, and the report's sections.
2. It calls the new MCP tool `get_monthly_report(month)`. The **reports module** reads the person's expenses of that
   month and the month before (the expenses and categories modules' queries), then runs the skill's script,
   `skills/monthly-report/scripts/compute_report.py`, with them as JSON. The script adds up the total and the change,
   the categories and payment methods (with their shares), the five biggest expenses and the daily average.
3. The server checks the script's answer (`MonthlyReport`) and the model gets the figures as the tool's result; the
   person sees them as the **report card**. The model's reply is two or three sentences, as the skill says.
4. The card's **Download CSV** and **Download report (.md)** buttons run a function in the browser
   (`downloadReport`), which fetches the file from `GET /api/v1/reports/monthly/{month}/{csv|md}` as the signed-in
   person and saves it. The files are written by the server in the person's language.

**Why the server runs the script, not the model.** A script is code: running whatever the model asked for would make
every prompt injection a code execution. So the model never runs anything and never sees the script; the server runs
one listed script, from the repository, with only the person's own expenses as input, in a separate process with a
time limit (D209). The script exists so the arithmetic is exact and repeatable (decimals, rounding half up), instead
of a model adding numbers in its head.

**Why a function in the browser for the downloads.** A button can either send an event to the agent or run a function
the renderer knows (A2UI's `functionCall`). A download needs neither the agent nor a run: the browser fetches the file
with the person's own session. The card carries only the month and the format; the browser builds the address, so a
card can't send it anywhere else.

| Where | What |
|---|---|
| `skills/monthly-report/SKILL.md`, `scripts/compute_report.py` | the skill (steps, reply, tone, sections) and the script that works the figures out |
| `backend/app/core/skills.py`, `infrastructure/skills.py` | `SkillLibrary.run_script`: one listed script, a child process, JSON in and out, 10 seconds at most |
| `backend/app/modules/reports/` | the new module: `MonthlyReports` (read, run the script, check), the markdown and CSV, the routes |
| `backend/app/modules/mcp/tools/get_monthly_report.py` | the tool, after `delete_expense` |
| `assistant/a2ui/report_card.py`, `models.py` | the card; a button's action may now be a `functionCall` (forms still refuse one) |
| `web/src/features/assistant/a2ui/functions/` | the allow-listed client functions: `downloadReport` |
| `web/src/features/assistant/a2ui/use-button-click.ts` | a click sends the event or runs the function |

**How it was checked:** 35 offline checks with a scripted model (D209): the model's input is what it was apart from the
new tool; the figures, the CSV (its header, every expense of the month, formulas neutralised, Hindi) and the markdown
(its sections, names escaped, Hindi); an empty month; bad months and formats; another person's report; a failing or
nonsense-answering script (502 with a text for people); the skill, the tool, the chips and the card with its two
function-call buttons and no address; forms refusing a function call. Every earlier suite passes. Live, 2 Gemini
calls: for "Can I get my monthly report for this month?", Gemini read the monthly-report skill on its own, then called
`get_monthly_report("2026-11")`.

### Try it

In the chat: "Give me my monthly report for this month". The chips show "Reading a skill…" then "Making the month's
report…", the card shows the figures, and its buttons save `spendwise-2026-11.csv` and `spendwise-2026-11.md`.
