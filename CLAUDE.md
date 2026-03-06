# Claude Code Instructions

**START HERE:** Read `.ai/principles.md` for the 7 core principles guiding all development work. That file is your mental framework for every decision.

For detailed operational specifics and reference material, see:

- `.ai/operations.md` - Project conventions, pre-commit validation gates, common procedures
- `agents/02a-architecture-guardian.md` - Deep dive on architecture boundaries
- `agents/04a-test-guardian.md` - Deep dive on test integrity
- `agents/07-session-continuity-agent.md` - Deep dive on session tracking
- `.ai/agents/08-ollama-delegation.md` - Ollama MCP tool delegation policy (use to reduce Claude token usage)

**Session Start**: When user greets you, activate session continuity mode:

1. Warm greeting (personalize it—vary language/style)
2. Quick check: `git status` (should be on feature branch, not main)
3. Check for uncommitted changes
4. Read `PROGRESS.md` to catch up on last session
5. Either summarize incomplete work or present backlog priorities

**Remember**: Principles over rules. When uncertain, identify which principle applies and use judgment.

**Tools**: Tell the user if any tools or MCPs are listed in .ai\agents or elsewhere but something is preventing those tools from being used
