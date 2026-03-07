# GitHub Copilot Instructions

**START HERE:** Read `.ai/principles.md` for the 7 core principles guiding all development work. That file is your mental framework for every decision.

For detailed operational specifics and reference material, see:

- `.ai/instructions.md` - Full operational details, pre-commit validation gates, project conventions
- `agents/02a-architecture-guardian.md` - Deep dive on architecture boundaries
- `agents/04a-test-guardian.md` - Deep dive on test integrity
- `agents/07-session-continuity-agent.md` - Deep dive on session tracking
- `.ai/agents/08-ollama-delegation.md` - Ollama MCP delegation policy for mechanical, code-focused tasks

**Ollama Usage Expectation**: Prefer Ollama for mechanical drafting/analysis (code generation, cross-file consistency checks, test scaffolding), then perform final judgment and validation in Copilot before committing.

**Session Start**: When user greets you, activate session continuity mode:

1. Warm greeting (personalize it—vary language/style)
2. Quick check: `git status` (should be on feature branch, not main)
3. Check for uncommitted changes
4. Read `PROGRESS.md` to catch up on last session
5. Either summarize incomplete work or present backlog priorities

**Remember**: Principles over rules. When uncertain, identify which principle applies and use judgment.
