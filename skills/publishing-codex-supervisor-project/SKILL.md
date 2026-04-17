---
name: publishing-codex-supervisor-project
description: Use when packaging a local Codex Supervisor implementation into a reusable GitHub project, preparing repository docs, excluding runtime state, and pushing both the tool and its operator skills to a new remote repository.
---

# Publishing Codex Supervisor Project

## Overview

Publish the project only after the runtime path, operator commands, tests, and skill docs are coherent.
Repository content should contain source, tests, docs, and skills, but never live daemon state.

## When to Use

- A local supervisor prototype must become a shareable GitHub repository.
- The repository needs install docs, operator docs, and reusable skills.
- Runtime `data/` artifacts must be excluded before publishing.

## Required Repository Shape

- `src/` for package code
- `tests/` for regression coverage
- `README.md` for install and operator workflow
- `skills/` for reusable best-practice skills
- `docs/` for plans or supporting design material
- `.gitignore` excluding runtime `data/`

## Publish Sequence

1. Verify the runtime project state:

```powershell
python -m pytest tests -q
```

2. Verify the runtime directory is ignored:

```powershell
git status --ignored --short
```

3. Commit all intended source, docs, and skills changes.
4. Create the GitHub repository with `gh repo create`.
5. Add or confirm `origin`.
6. Push the current branch and set upstream.

## GitHub Commands

```powershell
gh repo create <owner>/<repo> --public --source . --remote origin --push
```

If `origin` already exists:

```powershell
git remote set-url origin https://github.com/<owner>/<repo>.git
git push -u origin <branch>
```

## Publishing Guardrails

- Do not commit `data/`, daemon locks, runtime logs, or local DB files.
- Do not publish claims without fresh test output.
- Keep README examples aligned with the actual CLI surface.
- Publish the skills alongside the code so the repo remains self-contained.

## Verification Before Announcing Success

Run all of these fresh:

```powershell
python -m pytest tests -q
git status --short --branch
git remote -v
gh repo view --json name,url,isPrivate
```

Report the actual repo URL, branch state, and any remaining local-only artifacts.
