# Documentation Standards for AI Agents

## Purpose

This guide defines standards for what to include and exclude in documentation, with specific rules about code examples and content organization.

## Core Principle: Documentation Over Code

**Primary Rule**: Documentation should explain concepts, patterns, and principles. Code should only be included when absolutely necessary to illustrate complex scenarios that cannot be explained through text alone.

### When to Include Code

✅ **Include code ONLY when:**

1. **Complex algorithm or logic** that is difficult to explain in prose
2. **Security-critical patterns** (e.g., proper password hashing, SQL injection prevention)
3. **Subtle bugs or anti-patterns** that need visual demonstration
4. **Configuration examples** that have specific syntax requirements
5. **API contracts** where exact structure matters
6. **Before/after comparisons** showing refactoring or improvements

### When to EXCLUDE Code

❌ **Do NOT include code for:**

1. **Simple, self-explanatory concepts** (e.g., "use meaningful variable names")
2. **Standard patterns** that developers should already know
3. **Trivial examples** that can be explained in one sentence
4. **Repetitive demonstrations** of the same pattern
5. **Complete implementations** - link to external resources instead
6. **Framework-specific boilerplate** - reference official documentation
7. **Multiple language variations** of the same concept (pick one representative example)

## Documentation Structure Rules

### 1. Explain First, Show Later

````markdown
✅ Good Structure:

## Error Handling

Always validate inputs before processing. When validation fails, return
specific error messages that help users understand what went wrong. Use
typed exceptions for different error categories.

[Only include code if the pattern is non-obvious]

❌ Bad Structure:

## Error Handling

```javascript
function processUser(data) {
  if (!data.email) throw new Error("Email required");
  if (!data.name) throw new Error("Name required");
  // ... 50 lines of obvious validation code
}
```
````

````

### 2. Use Prose for Principles
```markdown
✅ Good:
**Single Responsibility Principle**: Each function should do one thing well.
If a function validates data, transforms it, saves to database, and sends
emails, it's doing too much. Split it into separate functions with clear names.

❌ Bad:
**Single Responsibility Principle**:
[Followed by 100 lines of code example]
````

### 3. Link Instead of Embedding

```markdown
✅ Good:
For JWT implementation, follow the official JWT.io best practices:
https://jwt.io/introduction

Key points to remember:

- Always validate signatures
- Set appropriate expiration times
- Store tokens securely

❌ Bad:
[50 lines of JWT implementation code that's available in every JWT library]
```

### 4. Use Tables and Lists for Comparisons

```markdown
✅ Good:
| Pattern | When to Use | When to Avoid |
|---------|-------------|---------------|
| Singleton | Global configuration | Business logic objects |
| Factory | Complex object creation | Simple object instantiation |

❌ Bad:
[Code example for Singleton]
[Code example for Factory]
[Code example for Builder]
[etc.]
```

## Code Example Guidelines

### Size Limits

- **Maximum 15 lines** for any single code example
- **Maximum 3 code examples** per section
- **Maximum 30% of document** should be code

### Code Example Template

When code IS necessary, use this format:

````markdown
### [Concept Name]

[2-3 sentence explanation of the concept]

**Why this matters**: [1 sentence on importance]

**Example of the issue**:

```language
// ❌ Bad: [What's wrong]
[Minimal code showing the problem - max 5 lines]
```
````

**Correct approach**:

```language
// ✅ Good: [What's right]
[Minimal code showing the solution - max 10 lines]
```

**Key takeaway**: [1 sentence summarizing the lesson]

````

### Annotations in Code
Every code block must have:
- ✅ or ❌ prefix indicating good/bad
- Brief comment explaining why
- Focused on ONE concept per example

```javascript
// ❌ Bad: Multiple concepts mixed together
function processOrder(order) {
  // validation, transformation, persistence, email, logging all mixed
  // ... 50 lines
}

// ✅ Good: Single responsibility
function processOrder(order) {
  validateOrder(order);
  const processed = transformOrderData(order);
  const saved = await saveOrder(processed);
  await sendConfirmation(saved);
  return saved;
}
````

## Content Organization

### Hierarchy of Information

1. **Concept** (what and why)
2. **Guidelines** (how to apply)
3. **Checklist** (what to verify)
4. **Examples** (only if necessary)
5. **References** (where to learn more)

### Section Template

```markdown
## [Topic Name]

### Overview

[2-3 sentences explaining the concept and its importance]

### Best Practices

- Practice 1: [Brief description]
- Practice 2: [Brief description]
- Practice 3: [Brief description]

### Common Pitfalls

- Pitfall 1: [What to avoid and why]
- Pitfall 2: [What to avoid and why]

### Checklist

- [ ] Item 1
- [ ] Item 2
- [ ] Item 3

### Further Reading

- [Resource 1](link)
- [Resource 2](link)

[Code examples ONLY if absolutely necessary]
```

## What to Include in Each Guide

### Requirements Gathering Guide

**Focus on**: Questioning techniques, documentation templates, requirement types
**Include**: Question lists, requirement formats, acceptance criteria templates
**Avoid**: Code examples (not relevant at this stage)

### Architecture Guide

**Focus on**: Decision-making processes, trade-off analysis, pattern selection
**Include**: Architecture Decision Record templates, comparison tables, diagrams
**Limit code to**: Configuration examples, infrastructure-as-code snippets (max 10 lines)

### Implementation Guide

**Focus on**: Principles (SOLID, DRY, KISS), naming conventions, code organization
**Include**: Brief examples for security patterns, anti-patterns vs solutions
**Avoid**: Complete implementations, framework tutorials, language basics

### Testing Guide

**Focus on**: Testing strategies, test structure, what to test
**Include**: Test naming conventions, AAA pattern, test pyramid diagram
**Limit code to**: Test structure examples (arrange-act-assert), mock/stub patterns

### Code Review Guide

**Focus on**: What to look for, how to provide feedback, review process
**Include**: Review checklists, feedback templates, severity labels
**Limit code to**: Critical security vulnerabilities, subtle bugs (max 5 lines each)

### Deployment Guide

**Focus on**: Deployment strategies, monitoring approaches, incident response
**Include**: Runbook templates, alert rule concepts, rollback procedures
**Limit code to**: Configuration examples (YAML/JSON), infrastructure-as-code snippets

## Anti-Patterns in Documentation

### ❌ Code Dumping

```markdown
Don't create documentation that's just a collection of code snippets.

Bad example:
"Here's how to implement authentication:"
[100 lines of authentication code]
[50 lines of authorization code]
[75 lines of session management code]

Good example:
"Authentication should verify user identity through:

1. Credential validation (check against stored hash)
2. Session creation (generate secure token)
3. Token storage (secure, HTTP-only cookies)

Use established libraries like Passport.js, NextAuth, or similar for
your tech stack rather than implementing from scratch."
```

### ❌ Tutorial Replication

```markdown
Don't recreate tutorials that exist elsewhere.

Bad: "Here's how to set up React..."
[Complete React tutorial]

Good: "For React setup, follow the official Create React App guide.
Key considerations for our project:

- Use TypeScript for type safety
- Enable strict mode
- Configure ESLint with our team rules"
```

### ❌ Language Wars

```markdown
Don't show the same pattern in multiple languages.

Bad:
"Here's validation in JavaScript:"
[code]
"Here's validation in Python:"
[code]
"Here's validation in Java:"
[code]

Good:
"Input validation should check for:

- Required fields present
- Correct data types
- Value constraints (length, range, format)
- Business rule compliance

Example in Python:
[Single focused example of validation pattern]"
```

### ❌ Obvious Examples

````markdown
Don't include code for self-explanatory concepts.

Bad:
"Use descriptive variable names:"

```python
# Bad
x = 5
# Good
user_age = 5
```
````

Good:
"Use descriptive variable names that reveal intent. Instead of single
letters or abbreviations, use full words that explain what the variable
represents in the business domain."

````

## Maintenance Guidelines

### When Updating Guides

1. **Review code-to-prose ratio**: Should be max 30% code
2. **Check example necessity**: Can this be explained in text?
3. **Verify example focus**: Does each example show ONE concept?
4. **Assess complexity**: Is this concept actually complex enough to warrant code?
5. **Update links**: Ensure external references are current
6. **Format**: Ensure the documents are formatted (use vscode `formatdocument` command)

### Red Flags
- More than 5 code blocks in a section
- Code blocks longer than 15 lines
- Repeated patterns across multiple examples
- Examples showing framework basics
- Tutorial-style step-by-step code

### Quality Checks
- [ ] Can a developer understand the concept without the code?
- [ ] Does the code show something non-obvious?
- [ ] Is the example minimal and focused?
- [ ] Are there links to comprehensive resources?
- [ ] Is the document scannable (good headers, lists, tables)?

## Formatting Standards

### Headers
- Use ATX-style headers (`#`, `##`, `###`)
- Maximum 3 levels deep
- Clear, action-oriented titles

### Lists
- Use `-` for unordered lists
- Use `1.` for ordered lists
- Maximum 2 levels of nesting
- Keep items concise (1-2 lines)

### Tables
- Use for comparisons, decision matrices, checklists
- Keep columns narrow (wrap text if needed)
- Include header row always

### Callouts
```markdown
**Important**: Use bold for critical information
**Note**: Use for additional context
**Warning**: Use for potential pitfalls
**Tip**: Use for helpful suggestions
````

### Code Blocks

```markdown
- Always specify language: `python, `javascript, etc.
- Use comments to annotate: // ❌ Bad, // ✅ Good
- Keep examples minimal and focused
- Prefer pseudo-code for complex algorithms
```

## Examples: Good vs Bad Documentation

### Example 1: Error Handling

❌ **Bad Documentation (Code-Heavy)**:

````markdown
## Error Handling

Here's how to handle errors:

```javascript
function createUser(data) {
  try {
    if (!data) {
      throw new Error("Data is required");
    }
    if (!data.email) {
      throw new Error("Email is required");
    }
    if (typeof data.email !== "string") {
      throw new Error("Email must be a string");
    }
    if (!data.email.includes("@")) {
      throw new Error("Email must be valid");
    }
    // ... 50 more lines
  } catch (error) {
    console.error(error);
    throw error;
  }
}
```
````

````

✅ **Good Documentation (Concept-Focused)**:
```markdown
## Error Handling

Handle errors at the appropriate level: validate at boundaries, catch at
handlers, and propagate with context.

### Validation Rules
- Check required fields first
- Validate types before values
- Provide specific error messages
- Use typed exceptions (ValidationError, NotFoundError, etc.)

### Error Propagation
- Add context as errors bubble up
- Log at the handling point, not everywhere
- Include correlation IDs for tracing
- Don't swallow errors silently

### Critical Pattern: SQL Injection Prevention
```python
# ❌ Bad: String concatenation
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ Good: Parameterized query
query = "SELECT * FROM users WHERE id = ?"
db.execute(query, [user_id])
````

**Why this matters**: Parameterized queries separate code from data,
preventing malicious input from being executed as SQL.

````

### Example 2: Testing Strategy

❌ **Bad Documentation (Code-Heavy)**:
```markdown
## Unit Testing

Here's a unit test:

```javascript
describe('UserService', () => {
  it('should create a user', async () => {
    const mockDb = {
      save: jest.fn().mockResolvedValue({ id: 1 })
    };
    const service = new UserService(mockDb);
    const result = await service.createUser({
      email: 'test@example.com',
      name: 'Test'
    });
    expect(result.id).toBe(1);
  });

  it('should update a user', async () => {
    // ... another 30 lines
  });

  // ... 10 more similar tests
});
````

````

✅ **Good Documentation (Strategy-Focused)**:
```markdown
## Unit Testing

Test behavior, not implementation. Focus on inputs, outputs, and side effects.

### Test Structure (AAA Pattern)
1. **Arrange**: Set up test data and dependencies
2. **Act**: Execute the function being tested
3. **Assert**: Verify the outcome

### What to Test
- **Happy path**: Expected behavior with valid inputs
- **Edge cases**: Boundaries, empty values, null/undefined
- **Error cases**: Invalid inputs, failed dependencies
- **Side effects**: Database calls, API requests, events emitted

### Test Independence
Each test should:
- Set up its own data (no shared state)
- Run in any order
- Clean up after itself

### Naming Convention
Pattern: `should_[expected behavior]_when_[condition]`
Example: `should_throw_ValidationError_when_email_is_invalid`

For test structure example, see:
https://kentcdodds.com/blog/common-mistakes-with-react-testing-library
````

## Summary Checklist

Before finalizing any documentation:

- [ ] **Concept clarity**: Can readers understand without code?
- [ ] **Code necessity**: Is each code example essential?
- [ ] **Example size**: All examples under 15 lines?
- [ ] **Code ratio**: Less than 30% of document is code?
- [ ] **Focus**: One concept per example?
- [ ] **Annotations**: All code blocks have ✅/❌ and comments?
- [ ] **Alternatives**: Are there links to comprehensive resources?
- [ ] **Structure**: Clear hierarchy with scannable headers?
- [ ] **Actionability**: Do readers know what to do next?
- [ ] **Maintenance**: Will this remain relevant over time?

## Key Principles Summary

1. **Documentation is for understanding, not copy-pasting**
2. **Principles over examples, concepts over code**
3. **Link to resources rather than recreating them**
4. **Show only what's complex, explain everything else**
5. **One example is better than five similar ones**
6. **Security and subtle bugs warrant code examples**
7. **Tables and lists beat walls of code**
8. **Checklists ensure completeness without verbosity**

Remember: The best documentation teaches developers to think correctly, not to write specific code.

---

## Session Continuity Standards

### Purpose

When working with AI assistants across multiple sessions, documentation must support easy context restoration. Follow these guidelines to ensure smooth session handoffs.

### Requirements for All Documentation

#### 1. Status Tracking

Every major document should include a status section when applicable:

```markdown
## Status

| Field        | Value                          |
| ------------ | ------------------------------ |
| Last Updated | YYYY-MM-DD                     |
| Status       | Draft / In Progress / Complete |
| Owner        | [Name or AI Session]           |
```

#### 2. Decision Logging

Document key decisions inline with rationale:

```markdown
**Decision**: Use PostgreSQL with TimescaleDB for time-series data
**Rationale**: Native time-series support, better query performance for metrics
**Date**: YYYY-MM-DD
**Alternatives Considered**: InfluxDB (rejected: additional infrastructure)
```

#### 3. Progress Checklists

Use markdown checklists for trackable items:

```markdown
### Implementation Checklist

- [x] Completed item
- [ ] Pending item
- [ ] Future item
```

## Pre-Commit Documentation Validation Checklist

**Before committing any documentation file (\*.md), verify**:

### Code Content Check

- [ ] Code represents ≤ 30% of document total lines
- [ ] Each code example ≤ 15 lines maximum
- [ ] ≤ 3 code examples per section
- [ ] Code ONLY included when absolutely necessary
  - ✅ Complex algorithms or logic
  - ✅ Security-critical patterns
  - ✅ Before/after refactoring comparisons
  - ❌ Simple self-explanatory concepts
  - ❌ Standard patterns everyone knows
  - ❌ Complete implementations (link instead)
- [ ] Full implementations linked to actual files, not embedded

### Structure Check

- [ ] Principles explained in prose BEFORE any code examples
- [ ] Complex concepts use tables/lists instead of code
- [ ] Section headings clearly distinguish architecture from implementation
- [ ] Documentation reads as "WHAT and WHY", not "HOW and WHERE"

### Completeness Check

- [ ] Architecture Guardian validation section present (if implementation doc)
  - Verifies no boundary violations
  - Lists what architectural rules are followed
- [ ] References to actual implementation files included (if applicable)
  - Script locations: `scripts/filename.py`
  - Test files: `tests/contract/integration/test_filename.py`
  - Model files: `src/database/models/filename.py`
- [ ] Test strategy linked to actual test files (if applicable)
- [ ] No orphaned references to non-existent files

### Validation Command

```bash
# Quick validation
bash scripts/validate-documentation.sh docs/04-implementation/your-doc.md

# Output should show:
# ✅ Code content within guidelines
# ✅ No full function definitions
# ✅ Architecture Guardian section present
```

---

### Session Handoff Checklist

Before ending an AI session, ensure:

- [ ] All modified files are documented
- [ ] Decisions made are recorded with rationale
- [ ] Progress checklists are updated
- [ ] Blockers and open questions are noted
- [ ] Next steps are clearly stated
- [ ] Session continuity doc is updated ([11-session-continuity.md](../docs/11-session-continuity.md))

### Agent-Specific Handoff Notes

Each agent guide includes a "Handoff Checklist" section. Update these with session-specific context:

- **Requirements Agent**: Document open questions and stakeholder responses needed
- **Architecture Agent**: Note pending design decisions and trade-offs being evaluated
- **Implementation Agent**: Track which functions/modules are partially complete
- **Testing Agent**: List tests written vs tests still needed
- **Code Review Agent**: Document review findings and unresolved issues
- **Deployment Agent**: Track deployment state and any rollback information

### Cross-Reference Standards

Always link to related documents rather than duplicating information:

```markdown
For session continuity guidelines, see [11-session-continuity.md](../docs/11-session-continuity.md)
For implementation progress, see [07-implementation-plan.md](../docs/07-implementation-plan.md)
```

### File Naming for Session Artifacts

When creating session-specific artifacts:

```
docs/sessions/YYYY-MM-DD-session-notes.md    # Session summaries
docs/decisions/ADR-NNN-decision-title.md     # Architecture Decision Records
```
