# Git workflow

## Identity for this repo only

This repo uses its own commit name and email, set with `--local`, so they're saved in this repo's
`.git/config` only. The global git identity (used by every other repo on the machine) is unchanged.

```powershell
git config --local user.name "<name>"
git config --local user.email "<email>"

git config --local --list     # see what this repo uses
git config --global --list    # see the machine-wide defaults (unchanged)
```

## Before every commit

1. `git status`: nothing from the "never commit" list should appear.

   | Commit | Never commit |
   |---|---|
   | Source code, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `docs/`, `run.ps1`, `.vscode/settings.json` | `.venv/`, `__pycache__/`, `.env`, `*.db` |

2. Make sure no real API key is staged. `git diff --cached --name-only` must not list `.env`, and
   searching the staged changes for the first few characters of your key should find nothing:
   `git diff --cached | Select-String '<first 8 characters of your key>'`.
3. Keep the code and its docs in the same commit (phase notes, decisions, README).

The `LF will be replaced by CRLF` warnings when staging are harmless on Windows.

## GitHub

The repo is pushed to a private GitHub repo, `sanjeevgnrgy/spendwise` (see [decisions.md](decisions.md) D37):

```powershell
git remote -v      # shows https://sanjeevgnrgy@github.com/sanjeevgnrgy/spendwise.git
git push           # after committing; main tracks origin/main
```

**Why the username is in the URL:** Git Credential Manager remembers one login per GitHub account. This
machine already has a login for a different account. Putting `sanjeevgnrgy@` in the URL makes this repo use
its own login, and other repos keep using the usual account. The first push opens a browser to sign in as
that account once; it's remembered after that.

**Setting this up on another repo:**
1. Create an **empty** repo on github.com: no README, `.gitignore` or license, so there's no history to merge.
2. `git remote add origin https://<github-username>@github.com/<owner>/<repo>.git`
3. `git push -u origin main`
