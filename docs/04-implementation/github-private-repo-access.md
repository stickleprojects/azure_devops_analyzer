# GitHub Private Repository Access - API Constraints

## Overview

Private repository visibility in GitHub depends on endpoint type, identity context, and token scope. This document defines expected behavior and extractor decision rules.

## Endpoint Behavior Matrix

| Endpoint style              | Private visibility                  | Key constraint                              |
| --------------------------- | ----------------------------------- | ------------------------------------------- |
| Authenticated user endpoint | Full for repos the token can access | Requires token with private-repo scope      |
| Named user endpoint         | Public repos only                   | Cannot enumerate another user private repos |
| Organization endpoint       | Conditional                         | Requires org membership and permissions     |

## Token Scope Impact

| Token scope       | Private repository visibility | Typical result                            |
| ----------------- | ----------------------------- | ----------------------------------------- |
| public-only scope | No                            | Only public repositories returned         |
| repo full scope   | Yes                           | Public plus private repositories returned |
| partial scopes    | Mixed                         | Visibility depends on granted permissions |

## Extractor Decision Model

The extractor uses include_private together with target identity to choose a retrieval mode.

### include_private true

- Authenticated self-target: request all visible repositories.
- Organization target: request all repositories and rely on org membership permissions.
- Other user target: API still limits to public repositories.

### include_private false

- Authenticated self-target: request public-only repositories.
- Organization target: request public-only repositories.
- Other user target: still public-only behavior.

## Access-Mode Logging

Runtime logs should always record which mode was used, for example:

- organization access mode
- authenticated user access mode
- named user public-only mode

This makes private visibility issues diagnosable without tracing internal call paths.

## Operational Scenarios

### Scenario: Own Account

Expected result: private repositories are visible only when token scope allows private access.

### Scenario: Organization

Expected result: private organization repositories are visible only when the token identity is a member with sufficient permissions.

### Scenario: Another User

Expected result: only public repositories are visible, regardless of include_private.

## Caching Considerations

Cache keys include include_private state, so public-only and include-private calls are isolated entries.

Operational implication:

- A public-only cache entry does not block a later include-private fetch.
- Include-private fetch still depends on API permissions and may return public-only data if access is insufficient.

## Debugging Checklist

1. Confirm token scope includes private access where required.
2. Confirm target identity is self, org member, or other user as expected.
3. Confirm runtime logs show the expected access mode.
4. Confirm cache key differs between include_private true and false calls.

## Architecture Guardian

This document is implementation-focused guidance and preserves architecture boundaries:

- Extractor decides retrieval mode only.
- Storage layer remains the sole writer to persistence.
- Workflow layer orchestrates but does not embed API policy logic.

## Summary Table

| Target type        | include_private true                     | include_private false |
| ------------------ | ---------------------------------------- | --------------------- |
| Authenticated self | Public plus private if scope allows      | Public only           |
| Organization       | Public plus private if membership allows | Public only           |
| Other user         | Public only                              | Public only           |

## See Also

- [src/extractors/github/extractor.py](../../../src/extractors/github/extractor.py)
- [docs/03-operations/feature-development-workflow.md](../03-operations/feature-development-workflow.md)
