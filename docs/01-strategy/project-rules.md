# Project Rules and Guidelines

## Overview

These rules apply to all development and documentation activities to ensure the project remains concise, maintainable, and focused.

## 1. Documentation Standards

- **No Source Code**: Do not include implementation code in markdown documentation unless describing a complex algorithm or specific edge case.
- **Focus on Logic**: Describe _what_ the system does and _why_, not _how_ (leave implementation details to the code).
- **Single Source of Truth**: Do not duplicate architectural decisions across multiple files. Reference the primary definition.

## 2. Coding Standards

- **Modular Functions**: Keep functions small (< 50 lines) and focused on a single task.
- **Type Hints**: Use Python type hints for all function arguments and return values.
- **Configuration**: Externalize all configuration (secrets, timeouts, schedules). No hardcoded values.

## 3. Architecture Principles

- **Idempotency**: All workflows must be idempotent. Re-running a job should be safe.
- **Fail Fast, Recover Gracefully**: Handle errors at the task level. Don't crash the scheduler for a single repo failure.
- **Incremental First**: Design all collectors to support incremental updates from day one.

## 4. AI Assistant Interaction

- **Concise Responses**: When generating code or text, prioritize brevity.
- **Diffs Only**: Provide `diff` blocks for code changes rather than reprinting entire files.
- **Context Awareness**: Assume knowledge of the existing technology stack (Python 3.11, PostgreSQL, APScheduler/Celery).
