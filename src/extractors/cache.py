"""
Caching decorator for extractor methods.

Eliminates redundant API calls within a single extraction run by caching
results on the extractor instance. The cache is session-scoped — it lives
as long as the extractor instance and clears automatically when the run ends.
"""

import functools
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_NONE_SENTINEL = "__CACHE_NONE__"


def _normalize_arg(arg):
    """Convert an argument to a stable, hashable string for cache keys.

    - datetime  → ISO-8601 string  (avoids object identity issues)
    - None      → sentinel string  (distinguishes from the string "None")
    - anything else → str(arg)
    """
    if arg is None:
        return _NONE_SENTINEL
    if isinstance(arg, datetime):
        return arg.isoformat()
    return str(arg)


def _make_cache_key(method_name, args, kwargs):
    """Build a deterministic string key from method name + call arguments.

    ``args`` should already exclude ``self`` (the decorator handles that).
    """
    parts = [method_name]
    parts.extend(_normalize_arg(a) for a in args)
    for k in sorted(kwargs):
        parts.append(f"{k}={_normalize_arg(kwargs[k])}")
    return "|".join(parts)


def cached(method):
    """Decorator that caches the return value of an extractor instance method.

    Requirements on the instance (``self``):
        * ``self._cache``        — dict used as the store
        * ``self._cache_hits``   — int counter
        * ``self._cache_misses`` — int counter

    These are initialised by ``RepositoryExtractor.__init__``.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        key = _make_cache_key(method.__name__, args, kwargs)

        method_name = method.__name__
        if method_name not in self._cache_method_stats:
            self._cache_method_stats[method_name] = {"hits": 0, "misses": 0}

        if key in self._cache:
            self._cache_hits += 1
            self._cache_method_stats[method_name]["hits"] += 1
            logger.debug("Cache HIT  %s", key)
            return self._cache[key]

        self._cache_misses += 1
        self._cache_method_stats[method_name]["misses"] += 1
        logger.debug("Cache MISS %s", key)
        result = method(self, *args, **kwargs)
        self._cache[key] = result
        return result

    return wrapper
