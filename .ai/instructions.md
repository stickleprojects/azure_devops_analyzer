# AI Agent Instructions (Legacy Reference)

This file has been consolidated for clarity. Start with the simplified structure below instead.

---

## Quick Navigation

**Principles** (start here, read this first):

- `.ai/principles.md` - 7 core principles that guide all development work

**Operations** (reference when doing work):

- `.ai/operations.md` - Project conventions, procedures, pre-commit gates

**Deep Dives** (reference for specific topics):

- `agents/02a-architecture-guardian.md` - Architecture boundaries and design
- `agents/04a-test-guardian.md` - Test integrity and test types
- `agents/07-session-continuity-agent.md` - Session tracking and continuity
- `agents/00-documentation-standards.md` - Documentation guidelines

**Both Copilot and Claude**:

- `.github/copilot-instructions.md` - Copilot-specific instructions (points to principles)
- `CLAUDE.md` - Claude Code-specific instructions (points to principles)

---

## Why This Change?

The previous structure had:

- 70+ scattered rules across multiple files
- Overlapping instructions with contradictions
- Heavy emphasis on rules, leading to selective compliance
- Difficulty finding information

The new structure has:

- 7 core principles that enable judgment
- Clear separation: principles (mental framework) + operations (how-to) + references (details)
- Single entry point for both agents
- Easier to find and update information

---

## For Agents Using These Instructions

**If you're Claude or GitHub Copilot:**

1. Read `.ai/principles.md` to understand the 7 core principles
2. Use `.ai/operations.md` for project-specific conventions
3. Check the `agents/` directory for deep dives on specific topics
4. When uncertain, identify which principle applies and use judgment

That's it. Principles over rules.

---

## Legacy Content Preserved

The previous version of this file had detailed guidance on:

- Tone and personality (greeting style, communication style, session wrap-ups)
- Session continuity agent (activation, triggers, formats)
- Architecture guardian (boundaries, checks, auto-approve criteria)
- Test guardian (non-negotiable requirements, test types)
- Pre-commit validation (5 gates)
- Project conventions (Docker, environment, Python, code style, testing)

All of this content is preserved and distributed across:

- `.ai/principles.md` (7 core principles)
- `.ai/operations.md` (operational details and conventions)
- `agents/` (deep-dive reference documents)

If you need to find something specific, search across these files or ask the user for clarification.
