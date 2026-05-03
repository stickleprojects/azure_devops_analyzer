# Claude Code Instructions

**START HERE:** Read `.ai/principles.md` for the 7 core principles guiding all development work. That file is your mental framework for every decision.

For detailed operational specifics and reference material, see:

- `.ai/operations.md` - Project conventions, pre-commit validation gates, common procedures
- `agents/02a-architecture-guardian.md` - Deep dive on architecture boundaries
- `agents/04a-test-guardian.md` - Deep dive on test integrity
- `agents/07-session-continuity-agent.md` - Deep dive on session tracking

**Session Start**: When user greets you, activate session continuity mode:

1. Warm greeting (personalize it—vary language/style)
2. Quick check: `git status` (should be on feature branch, not main)
3. Check for uncommitted changes
4. Read `PROGRESS.md` if it exists to catch up on last session
5. Either summarize incomplete work or present backlog priorities

**Environment Setup**: If `.env` is missing or incomplete, generate it by running `./Start-RepoAnalysis.sh --regenerate-env` (or `./start-repoanalysis.sh --regenerate-env`) and have the user answer the interactive prompts.

**CI/Test Parity**: For any CI, test, fixture, schema, or migration change, follow `.ai/operations.md` Gate 3.6 (CI/Local Parity Check) and validate with Docker using CI-equivalent test scopes before committing.

**Remember**: Principles over rules. When uncertain, identify which principle applies and use judgment.

**Skills**: Project skills have two locations:

- `.ai/skills/` — source of truth (edit skills here)
- `.claude/skills/` — deployed copy (loaded by Claude Code automatically on checkout)

At session start, check for drift between the two:

```
diff -rq .ai/skills/ .claude/skills/
```

If there are differences, alert the user — the deployed copy is out of sync with the source.

**Tools**: Tell the user if any tools or MCPs are listed in .ai\agents or elsewhere but something is preventing those tools from being used
