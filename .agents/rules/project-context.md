---
trigger: always_on
---

# RiskLens — Project Context

Full engineering spec: docs/implementation.md — always read the relevant
Phase section from this file before starting work on that phase.

## Session Start Protocol (mandatory, every session)
1. Read docs/PROGRESS.md.
2. Run `git log --oneline -10` and check the actual files/folders that
   exist against the "Files to Create" list for the current phase in
   docs/implementation.md.
3. If PROGRESS.md and the actual repo state disagree, trust the repo,
   not the notes — state the discrepancy to me before continuing.
4. Only after 1–3, summarize what's actually done and what remains in
   the current phase, then proceed.

## Session End Protocol
Before ending a session or when told to wrap up: commit any uncommitted
work, then update docs/PROGRESS.md with a specific, concrete note (not
"in progress" — say exactly which files are done, which are partial,
and what the very next step is).

## Scope Discipline
- Only touch files listed under the current phase's "Files/Directories
  To Create" or "To Modify" in docs/implementation.md.
- If completing the phase properly seems to require touching a file
  outside that list, or deviating from what the phase describes, stop
  and tell me before doing it — do not silently expand scope.

## Working Rules
- Commit after every logical unit of work (one file or one function
  group), not just at the end of a phase. Use Conventional Commits
  (feat/fix/test/chore, with scope) matching the phase's Git Commit
  Strategy in docs/implementation.md.
- Never modify quant/ (or any file with financial/statistical logic)
  without a corresponding test in the same commit.
- Follow docs/implementation.md §9 folder structure and naming
  conventions exactly — do not introduce new top-level patterns.
- If two parallel agents are running, only work within the file scope
  I've explicitly assigned you — never edit a file outside it, even if
  it seems related.