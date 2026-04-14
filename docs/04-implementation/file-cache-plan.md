# Plan: File-Based Cache for Extractor Decorator

## Goal

Add optional file-based caching to the existing extractor cache decorator so it checks RAM cache first, then file cache, then calls the API and stores in both caches.

## Requirements

- New env var to enable file cache: `EXTRACTOR_FILE_CACHE_ENABLED` (default: `false`).
- New env var for cache path: `EXTRACTOR_FILE_CACHE_PATH` (default: `.cache` at project root).
- If enabled, decorator flow: RAM hit -> return, else file hit -> return (also hydrate RAM), else call -> store to file + RAM -> return.

## Design Decisions

- Keep file cache in the existing `@cached` decorator to preserve order and stats.
- Use deterministic, hashed filenames derived from cache key (e.g., `sha256`).
- Use JSON serialization for cache payloads.
- Use atomic writes (write temp file then rename) to avoid partial reads.
- Cache directory structure grouped by method name to reduce file count per directory.

## Implementation Steps

1. Add env vars to [/.env.example](../../.env.example) and document in [docs/03-operations/docker-setup.md](../03-operations/docker-setup.md) and optionally [README.md](../../README.md).
2. Add config helpers in [src/extractors/cache.py](../../src/extractors/cache.py):
   - Resolve project root (reuse `_find_project_root` from `src/config/github.py`).
   - Parse `EXTRACTOR_FILE_CACHE_ENABLED` and `EXTRACTOR_FILE_CACHE_PATH`.
3. Implement file cache helpers in [src/extractors/cache.py](../../src/extractors/cache.py):
   - `*_get_file_cache_dir()` -> Path
   - `*_get_file_cache_path(key, method_name)` -> Path
   - `*_read_file_cache(path)` -> result or sentinel
   - `*_write_file_cache(path, value)` -> None (atomic write)
4. Update `cached` decorator flow:
   - RAM hit -> increment stats and return.
   - If enabled, check file cache -> on hit increment stats, hydrate RAM, return.
   - On miss, call method, then write file cache (if enabled), store in RAM, return.
5. Extend unit tests in `tests/unit/test_extractor_cache.py`:
   - File cache miss/hit behavior.
   - Default path resolution.
   - Disabled flag no file reads/writes.
   - Error handling (corrupt cache file should be treated as miss).

## Open Questions

- Confirm env var naming (`EXTRACTOR_FILE_CACHE_ENABLED`, `EXTRACTOR_FILE_CACHE_PATH`).
- Confirm serialization format (default: JSON).

## Acceptance Criteria

- With file cache enabled, a second run hits file cache with no API call and populates RAM cache.
- With file cache disabled, behavior is unchanged.
- Unit tests pass and no regression in existing cache behavior.

## Architecture Guardian

This file-cache extension preserves core boundaries:

- Caching remains an extractor support concern, not a workflow responsibility.
- Workflow orchestration remains unchanged and does not embed cache policy logic.
- Storage/database layers remain the only persistence writers for analysis data.
- Platform extractor implementations stay isolated from one another.
