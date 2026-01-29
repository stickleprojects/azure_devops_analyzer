# Session Continuity Guide

## Purpose

This document provides a standardized approach for resuming AI development sessions, ensuring smooth handoffs and minimizing context loss between sessions. It covers both how to use the Session Continuity Agent and the technical specification of how session continuity works.

---

## Quick Reference: Prompting the Agent

### ✅ Starting Your Session - Use These Prompts

**When you begin work:**

- "good morning"
- "let's continue"
- "pick up where we left off"
- "what should I work on?"

**If greeting doesn't activate the agent:**

- "analyze last session"
- "show me the backlog"
- "what's the priority list?"

### What Happens

The agent will:

1. Read your last session from PROGRESS.md
2. Check git status for uncommitted work
3. Present either:
   - **Incomplete work** → Summary + suggestion to continue
   - **Completed work** → Backlog priorities with recommendations

### Example Interaction

```
You: "good morning"

Agent: Good morning! Welcome back. 🌅

📋 Last Session Summary (2026-01-23)

Completed:
- Fixed GitHub API private repository bug
- All 34 tests passing

In Progress:
None - previous session complete

Top Priority Backlog:
1. 🔴 HIGH - Dependency API Integration (70% complete)
2. 🟡 MEDIUM - Repository Language Detection (quick win)

Recommendation: Start with #2 for a quick win.
Which would you like to tackle?
```

---

## During Your Work Session

### ✅ Check Task Completion

**When you think you're done with a task:**

- "is this task complete?"
- "check if I'm done"
- "am I ready to mark this complete?"
- "review task status"

**What the agent checks:**

- ✓ Tests passing (no errors)
- ✓ Git status (committed or staged)
- ✓ No TODOs in modified files
- ✓ Implementation complete

### Example Interaction

```
You: "is this task complete?"

Agent: Let me check the completion criteria...

✓ Tests: 12 tests, all passing
✓ Git: Changes committed 5 minutes ago
✓ Errors: None detected
✓ Implementation: All planned changes complete

🎉 Task appears complete!

Would you like me to:
1. Mark task as complete in todo list
2. Update PROGRESS.md with session entry
3. Update requirements-status.md

Reply 'yes' to proceed.
```

---

## Technical Specification

### Quick Resume Checklist

When starting a new AI session, provide the AI with this information:

### 1. Current Project Status

- [ ] **Phase**: Which implementation phase are we in? (see [07-implementation-plan.md](07-implementation-plan.md))
- [ ] **Last completed task**: What was the last thing completed?
- [ ] **In-progress work**: What was being worked on when the session ended?
- [ ] **Blockers**: Any issues or decisions pending?

### 2. Recent Changes

- [ ] **Modified files**: List files changed in the last session
- [ ] **New files created**: Any new modules or components added
- [ ] **Pending commits**: Are there uncommitted changes?

### 3. Context & Decisions

- [ ] **Key decisions made**: Architecture or design choices from previous sessions
- [ ] **Open questions**: Unresolved decisions needing input
- [ ] **Deferred items**: Things explicitly postponed for later

---

## Project Status Tracker

**Update this section at the end of each session.**

### Current State

| Field                 | Value                                       |
| --------------------- | ------------------------------------------- |
| **Current Phase**     | Phase 1: Foundation                         |
| **Current Week**      | Week 1                                      |
| **Last Session Date** | _[Update after each session]_               |
| **Session Focus**     | _[Brief description of what was worked on]_ |

### Implementation Progress

#### Phase 1: Foundation (Weeks 1-2)

**Week 1: Environment Setup**

- [ ] Set up development environment
- [ ] Configure Azure DevOps access
- [ ] Initialize version control (DONE - repo initialized)

**Week 2: Database Setup**

- [ ] Install PostgreSQL 15 and TimescaleDB
- [ ] Design and create database schema
- [ ] Create database migrations
- [ ] Implement basic data access layer
- [ ] Write unit tests for database operations

#### Phase 2: Core Analysis (Weeks 3-5)

_Not started_

#### Phase 3: Metrics Collection (Weeks 6-7)

_Not started_

#### Phase 4: Orchestration (Week 8)

_Not started_

#### Phase 5: Visualization (Weeks 9-10)

_Not started_

#### Phase 6: Production Hardening (Weeks 11-12)

_Not started_

---

## Session Handoff Template

Use this template at the end of each session:

````markdown
## Session Summary - [DATE]

### Completed This Session

- Item 1
- Item 2

### In Progress (Not Complete)

- Item with status/percentage
- Blocker or issue if any

### Files Modified

- `path/to/file1.py` - Description of changes
- `path/to/file2.py` - Description of changes

### Files Created

- `path/to/newfile.py` - Purpose

### Key Decisions Made

- Decision 1: Rationale
- Decision 2: Rationale

### Open Questions / Blockers

- Question needing answer
- Blocker needing resolution

### Next Session Should

1. First priority task
2. Second priority task
3. Third priority task

### Commands to Run First

```bash
# Any setup or verification commands for next session
git status
pip install -r requirements.txt
```
````

````

---

## Quick Reference Commands

### Check Project State

```bash
# See what's changed
git status

# See recent commits
git log --oneline -10

# See uncommitted changes
git diff

# See project structure
ls -la src/
````

### Verify Environment

```bash
# Check Python version
python --version

# Verify dependencies
pip list

# Run tests
pytest

# Check database connection
python -c "from src.database import engine; print('DB OK')"
```

---

## Key Project Files

When resuming, these files provide essential context:

| File                                                   | Purpose                            |
| ------------------------------------------------------ | ---------------------------------- |
| [00-quick-reference.md](00-quick-reference.md)         | System overview and quick commands |
| [07-implementation-plan.md](07-implementation-plan.md) | Full task breakdown by phase       |
| [10-requirements.md](10-requirements.md)               | Dependencies and environment setup |
| [docker-compose.yml](../docker-compose.yml)            | Service configuration              |
| [requirements.txt](../requirements.txt)                | Python dependencies                |

---

## Resume Prompt Template

Copy and customize this prompt when starting a new session:

```
I'm resuming work on the Repository Analysis System.

**Current Status:**
- Phase: [1-6]
- Last session: [date] - [what was done]
- In progress: [task being worked on]

**Recent Changes:**
- [List key files modified]

**Today's Focus:**
- [Primary goal for this session]

**Blockers/Questions:**
- [Any issues needing resolution]

Please review the project docs at docs/ and continue from where we left off.
```

---

## Session Log

Track session history here for reference:

| Date     | Focus          | Completed           | Notes         |
| -------- | -------------- | ------------------- | ------------- |
| _[Date]_ | _[Focus area]_ | _[Items completed]_ | _[Key notes]_ |

---

## Best Practices

### At Session Start

1. Share the current project status (use checklist above)
2. Reference this document: "See docs/11-session-continuity.md"
3. State the specific goal for the session
4. Mention any blockers or decisions needed

### During Session

1. Keep notes on decisions made
2. Track files being modified
3. Note any deferred items

### At Session End

1. Update the Project Status Tracker section above
2. Fill in the Session Handoff Template
3. Add entry to Session Log
4. Commit any work in progress with clear messages

### Commit Messages for Session Boundaries

Use clear commit messages that help with session resumption:

```bash
# Good: Descriptive of state
git commit -m "WIP: Implement repository scanner - fetch branches complete, file trees pending"

# Good: Clear completion marker
git commit -m "Complete: Azure DevOps API client with rate limiting and retry logic"

# Good: Session boundary marker
git commit -m "Session end: Database schema 80% complete, missing PR tables"
```

---

## Integration with Agent Instructions

All agent instruction files (in `agents/`) should:

1. Reference this document for session continuity
2. Include handoff checklists specific to their domain
3. Document decisions in a discoverable format

See [00-documentation-standards.md](../agents/00-documentation-standards.md) for documentation guidelines.
