# GitHub Copilot Session Continuity - User Guide

## Quick Reference: When to Prompt the Agent

This guide explains when and how to interact with the Session Continuity Agent to get the most value from your development sessions.

---

## Starting Your Session

### ✅ Use These Prompts

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

## Task Management

### ✅ Start a New Task

**Explicitly tell the agent what you're working on:**
- "start task: implement language detection"
- "working on FR-2.1 (language detection)"
- "let's tackle dependency API integration"

**Why this matters:**
The agent can't automatically track what you're working on. Explicitly stating it helps the agent provide better context and completion checks later.

### ✅ Manual Task Completion

**If you want to skip automated checking:**
- "mark task complete"
- "mark complete without checking"
- "I'm done, mark it"

**The agent will:**
- Mark task complete in todo list
- Optionally update documentation (if you approve)
- Suggest next steps

---

## Ending Your Session

### ✅ Document Your Progress

**Request documentation update:**
- "update progress log"
- "end session and document progress"
- "summarize today's work"
- "write session summary"

**What the agent documents:**
- What was completed
- Files modified
- Key decisions made
- Next steps for next session

### Example Interaction

```
You: "end session and document progress"

Agent: I'll create a progress log entry.

Summary of session:
- Implemented repository language detection (FR-2.1)
- Added 5 tests, all passing
- Modified: src/extractors/github/extractor.py
- Decision: Store byte counts for future recalculation

Next steps:
- Implement same feature for Azure DevOps
- Add dashboard visualization

Should I add this to PROGRESS.md?
```

---

## Common Scenarios

### Scenario 1: You Forgot Where You Left Off

```
You: "where did I leave off?"
or
You: "what was I working on?"

Agent: [Reads PROGRESS.md and presents summary]
```

### Scenario 2: You're Not Sure What to Work On

```
You: "what should I work on next?"
or
You: "show priority backlog"

Agent: [Analyzes requirements-status.md and presents sorted priorities]
```

### Scenario 3: Tests Are Failing

```
You: "is this task complete?"

Agent: Not quite. Found issues:
       ✗ Tests: 3 failures detected
       ✓ Git: Changes committed
       
       Tests must pass before marking complete.
       Would you like to see the test failures?
```

### Scenario 4: You Want to Skip Documentation

```
Agent: Should I update PROGRESS.md and requirements-status.md?

You: "just mark complete, I'll update docs later"

Agent: Task marked complete. Documentation skipped.
```

### Scenario 5: Greeting Didn't Activate Agent

```
You: "good morning"

[No agent response]

You: "analyze last session"

Agent: [Provides session summary as usual]
```

---

## Best Practices

### Do ✅

1. **Be explicit about starting tasks**
   - Say: "start task: implement X"
   - Not: [silently starts coding]

2. **Request completion checks when ready**
   - Say: "is this task complete?"
   - Not: [expect automatic detection]

3. **Use clear, direct prompts**
   - Say: "show backlog priorities"
   - Not: "uh, what's next?"

4. **Confirm or decline suggestions**
   - Agent asks: "Mark complete?" → Answer clearly
   - Don't leave agent waiting

5. **End sessions explicitly**
   - Say: "end session" or "update progress"
   - Helps maintain good documentation

### Don't ❌

1. **Don't expect automatic monitoring**
   - Agent can't check status every 30 seconds
   - Must explicitly ask "is complete?"

2. **Don't assume greeting always works**
   - If no response, try: "analyze session"
   - Greeting activation is best-effort

3. **Don't skip progress documentation**
   - Future-you will thank present-you
   - Use agent's help: "document progress"

4. **Don't work on tasks without telling agent**
   - Agent can't track what you're doing silently
   - State: "working on X" at start

---

## Customizing Completion Checks

### Strict Mode (Production Features)

```
You: "check if complete (strict)"

Agent: Checking with strict criteria:
       - All tests must pass
       - Must be committed (not just staged)
       - No TODO comments allowed
       - No linter errors
```

### Lenient Mode (Experimental Work)

```
You: "check if complete (lenient)"

Agent: Checking with lenient criteria:
       - Tests must pass
       - Git state flexible (staged OK)
       - TODOs acceptable
```

### Default Mode

```
You: "is this task complete?"

Agent: Checking standard criteria:
       - Tests pass
       - Committed or staged
       - No critical errors
```

---

## Troubleshooting

### Problem: Agent Doesn't Respond to Greeting

**Solution:**
Try explicit prompts:
- "analyze last session"
- "show backlog"
- "what should I work on?"

Greeting activation is probabilistic, not guaranteed.

### Problem: Agent Can't Find Progress Logs

**Solution:**
Agent looks in:
- `/PROGRESS.md` (root level)
- `/docs/PROGRESS.md` (summary)

If neither exists, tell the agent:
"I worked on X last time, what should I do next?"

### Problem: Agent Keeps Asking for Confirmation

**Solution:**
This is by design. Agent requires explicit approval for:
- Marking tasks complete
- Updating documentation
- Modifying files

You must confirm each action.

### Problem: Completion Check Says "Not Complete" But I Think It Is

**Solution:**
Ask for details:
"why isn't this complete?"

Agent will explain which criteria aren't met:
- Tests failing?
- Git not committed?
- Implementation incomplete?

Fix the issue or use manual completion: "mark complete anyway"

---

## Integration with Other Agents

The Session Continuity Agent works with:

- **Architecture Guardian** - Validates boundaries before suggesting tasks
- **Test Guardian** - Ensures tests are updated as part of completion
- **Implementation Agent** - Takes over once task is selected

All agents require **user interaction** - they assist, they don't automate.

---

## Summary: Key Takeaways

| Situation | What to Say | What Happens |
|-----------|-------------|--------------|
| **Starting work** | "good morning" or "analyze session" | Session summary + backlog priorities |
| **Checking completion** | "is this task complete?" | Criteria analysis + mark complete option |
| **Stuck on priorities** | "what should I work on?" | Sorted backlog with recommendations |
| **Ending session** | "end session" or "document progress" | Progress log update + summary |
| **Manual completion** | "mark task complete" | Skip checking, just mark done |
| **Need context** | "where did I leave off?" | Last session summary |

**Remember:** The agent is a **smart assistant** that helps when you ask, not an **autonomous system** that works automatically. Prompt it explicitly, and it will guide you effectively.

---

## Feedback & Improvements

As you use the Session Continuity Agent, you'll develop your own patterns. Common phrases that work well:

- Morning: "good morning, what's on the agenda?"
- Checking: "am I done with this?"
- Selecting: "let's do #2 from the backlog"
- Ending: "that's it for today, document progress"

If you find prompts that work consistently, consider adding them to your team's conventions.
