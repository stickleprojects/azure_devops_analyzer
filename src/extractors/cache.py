"""
Caching decorator for extractor methods.

Eliminates redundant API calls within a single extraction run by caching
results on the extractor instance. The cache is session-scoped — it lives
as long as the extractor instance and clears automatically when the run ends.
"""

import functools
import hashlib
import json
import logging
import os
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime
from importlib import import_module
from pathlib import Path

from src.config.github import _find_project_root

logger = logging.getLogger(__name__)

_NONE_SENTINEL = "__CACHE_NONE__"
_FILE_CACHE_ENABLED_ENV = "EXTRACTOR_FILE_CACHE_ENABLED"
_FILE_CACHE_PATH_ENV = "EXTRACTOR_FILE_CACHE_PATH"
_DEFAULT_FILE_CACHE_PATH = ".cache"
_FILE_CACHE_MISS = object()
_FILE_CACHE_TYPE_KEY = "__cache_type__"
_FILE_CACHE_DATA_KEY = "__cache_data__"
_FILE_CACHE_DATETIME_KEY = "__cache_datetime__"
_FILE_CACHE_TUPLE_KEY = "__cache_tuple__"


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


def _get_env_bool(var_name: str, default: bool = False) -> bool:
    value = os.environ.get(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _file_cache_enabled() -> bool:
    return _get_env_bool(_FILE_CACHE_ENABLED_ENV, default=False)


def _file_cache_root() -> Path:
    raw_path = os.environ.get(_FILE_CACHE_PATH_ENV, _DEFAULT_FILE_CACHE_PATH)
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return _find_project_root() / path


def _file_cache_dir(method_name: str) -> Path:
    return _file_cache_root() / method_name


def _file_cache_path(method_name: str, cache_key: str) -> Path:
    cache_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return _file_cache_dir(method_name) / f"{cache_hash}.json"


def _encode_cache_value(value):
    if isinstance(value, datetime):
        return {_FILE_CACHE_DATETIME_KEY: value.isoformat()}
    if is_dataclass(value):
        return {
            _FILE_CACHE_TYPE_KEY: f"{value.__class__.__module__}.{value.__class__.__qualname__}",
            _FILE_CACHE_DATA_KEY: _encode_cache_value(asdict(value)),
        }
    if isinstance(value, tuple):
        return {_FILE_CACHE_TUPLE_KEY: [_encode_cache_value(item) for item in value]}
    if isinstance(value, list):
        return [_encode_cache_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _encode_cache_value(item) for key, item in value.items()}
    return value


def _resolve_type(type_path: str):
    module_name, _, qualname = type_path.rpartition(".")
    module = import_module(module_name)
    attr = module
    for part in qualname.split("."):
        attr = getattr(attr, part)
    return attr


def _decode_cache_value(value):
    if isinstance(value, dict):
        if _FILE_CACHE_DATETIME_KEY in value:
            return datetime.fromisoformat(value[_FILE_CACHE_DATETIME_KEY])
        if _FILE_CACHE_TUPLE_KEY in value:
            return tuple(_decode_cache_value(item) for item in value[_FILE_CACHE_TUPLE_KEY])
        if _FILE_CACHE_TYPE_KEY in value and _FILE_CACHE_DATA_KEY in value:
            target_type = _resolve_type(value[_FILE_CACHE_TYPE_KEY])
            data = _decode_cache_value(value[_FILE_CACHE_DATA_KEY])
            if is_dataclass(target_type):
                return target_type(**data)
            return data
        return {key: _decode_cache_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_cache_value(item) for item in value]
    return value


def _read_file_cache(path: Path):
    try:
        payload = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _FILE_CACHE_MISS
    except OSError as exc:
        logger.debug("File cache read failed: %s", exc)
        return _FILE_CACHE_MISS

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return _FILE_CACHE_MISS

    return _decode_cache_value(data)


def _write_file_cache(path: Path, value) -> bool:
    try:
        payload = json.dumps(_encode_cache_value(value), ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        logger.debug("File cache serialization failed: %s", exc)
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(path.parent),
        )
        temp_file.write(payload)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_file.name, path)
        return True
    except OSError as exc:
        logger.debug("File cache write failed: %s", exc)
        return False
    finally:
        if temp_file is not None:
            try:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
            except OSError:
                pass


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
        file_cache_enabled = _file_cache_enabled()
        cache_path = None
        if file_cache_enabled:
            cache_path = _file_cache_path(method_name, key)
        if method_name not in self._cache_method_stats:
            self._cache_method_stats[method_name] = {"hits": 0, "misses": 0}

        if key in self._cache:
            self._cache_hits += 1
            self._cache_method_stats[method_name]["hits"] += 1
            logger.debug("Cache HIT  %s", key)
            return self._cache[key]

        if file_cache_enabled and cache_path is not None:
            cached_value = _read_file_cache(cache_path)
            if cached_value is not _FILE_CACHE_MISS:
                self._cache_hits += 1
                self._cache_method_stats[method_name]["hits"] += 1
                logger.debug("File Cache HIT  %s", key)
                self._cache[key] = cached_value
                return cached_value

        self._cache_misses += 1
        self._cache_method_stats[method_name]["misses"] += 1
        logger.debug("Cache MISS %s", key)
        result = method(self, *args, **kwargs)
        self._cache[key] = result
        if file_cache_enabled and cache_path is not None:
            _write_file_cache(cache_path, result)
        return result

    return wrapper
