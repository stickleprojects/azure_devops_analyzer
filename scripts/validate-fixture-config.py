#!/usr/bin/env python3
"""Validate tests/fixtures/scenarios/config.json structure and values."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def error(errors: List[str], message: str) -> None:
    errors.append(message)


def warn(warnings: List[str], message: str) -> None:
    warnings.append(message)


def require_dict(errors: List[str], value: Any, path: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        error(errors, f"{path} must be an object")
        return {}
    return value


def require_list(errors: List[str], value: Any, path: str) -> List[Any]:
    if not isinstance(value, list):
        error(errors, f"{path} must be an array")
        return []
    return value


def require_string(errors: List[str], value: Any, path: str) -> str:
    if not isinstance(value, str):
        error(errors, f"{path} must be a string")
        return ""
    return value


def require_bool(errors: List[str], value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        error(errors, f"{path} must be a boolean")
        return False
    return value


def validate_range(errors: List[str], obj: Dict[str, Any], path: str) -> None:
    for key in ("min", "max", "median"):
        if key not in obj:
            error(errors, f"{path}.{key} is required")
            continue
        if not isinstance(obj[key], int):
            error(errors, f"{path}.{key} must be an integer")
    if all(isinstance(obj.get(k), int) for k in ("min", "max", "median")):
        if obj["min"] > obj["max"]:
            error(errors, f"{path}.min must be <= max")
        if not (obj["min"] <= obj["median"] <= obj["max"]):
            error(errors, f"{path}.median must be between min and max")


def validate_diffstat(errors: List[str], obj: Dict[str, Any], path: str) -> None:
    for key in ("files_changed", "lines_added", "lines_removed"):
        if key not in obj:
            error(errors, f"{path}.{key} is required")
            continue
        value = obj[key]
        if not isinstance(value, dict):
            error(errors, f"{path}.{key} must be an object")
            continue
        validate_range(errors, value, f"{path}.{key}")


def validate_pr_status(errors: List[str], obj: Dict[str, Any], path: str) -> None:
    for key in ("merged", "open", "closed"):
        if key not in obj:
            error(errors, f"{path}.{key} is required")
            continue
        if not is_number(obj[key]):
            error(errors, f"{path}.{key} must be a number")
    if all(is_number(obj.get(k)) for k in ("merged", "open", "closed")):
        total = float(obj["merged"]) + float(obj["open"]) + float(obj["closed"])
        if not (math.isclose(total, 1.0, abs_tol=1e-6) or math.isclose(total, 0.0, abs_tol=1e-6)):
            error(errors, f"{path} values must sum to 1.0 (or all zero). Got {total:.3f}")
        for key in ("merged", "open", "closed"):
            if obj[key] < 0 or obj[key] > 1:
                error(errors, f"{path}.{key} must be between 0 and 1")


def validate_pattern(errors: List[str], name: str, obj: Dict[str, Any]) -> None:
    require_string(errors, obj.get("description"), f"patterns.{name}.description")
    for key in ("commits", "pull_requests"):
        if key not in obj:
            error(errors, f"patterns.{name}.{key} is required")
            continue
        if not isinstance(obj[key], dict):
            error(errors, f"patterns.{name}.{key} must be an object")
            continue
        validate_range(errors, obj[key], f"patterns.{name}.{key}")

    for key in ("commit_metadata", "pr_metadata"):
        if key not in obj:
            error(errors, f"patterns.{name}.{key} is required")
            continue
        if not isinstance(obj[key], dict):
            error(errors, f"patterns.{name}.{key} must be an object")
            continue
        validate_diffstat(errors, obj[key], f"patterns.{name}.{key}")

    if "pr_status" not in obj:
        error(errors, f"patterns.{name}.pr_status is required")
    else:
        if not isinstance(obj["pr_status"], dict):
            error(errors, f"patterns.{name}.pr_status must be an object")
        else:
            validate_pr_status(errors, obj["pr_status"], f"patterns.{name}.pr_status")


def validate_repo_template(errors: List[str], name: str, obj: Dict[str, Any], patterns: Dict[str, Any]) -> None:
    require_string(errors, obj.get("description"), f"repo_templates.{name}.description")
    pattern = require_string(errors, obj.get("pattern"), f"repo_templates.{name}.pattern")
    if pattern and pattern not in patterns:
        error(errors, f"repo_templates.{name}.pattern references unknown pattern '{pattern}'")

    languages = require_list(errors, obj.get("languages"), f"repo_templates.{name}.languages")
    for i, lang in enumerate(languages):
        require_string(errors, lang, f"repo_templates.{name}.languages[{i}]")

    themes = require_list(errors, obj.get("commit_message_themes"), f"repo_templates.{name}.commit_message_themes")
    for i, theme in enumerate(themes):
        require_string(errors, theme, f"repo_templates.{name}.commit_message_themes[{i}]")

    pr_themes = require_list(errors, obj.get("pr_title_themes"), f"repo_templates.{name}.pr_title_themes")
    for i, theme in enumerate(pr_themes):
        require_string(errors, theme, f"repo_templates.{name}.pr_title_themes[{i}]")

    if "overrides" not in obj:
        error(errors, f"repo_templates.{name}.overrides is required")
    else:
        if not isinstance(obj["overrides"], dict):
            error(errors, f"repo_templates.{name}.overrides must be an object")


def expand_repo_sets(
    errors: List[str],
    warnings: List[str],
    repo_sets: List[Dict[str, Any]],
    repo_templates: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    expanded: List[Tuple[str, Dict[str, Any]]] = []
    seen_names: set[str] = set()

    for i, repo_set in enumerate(repo_sets):
        path = f"repo_sets[{i}]"
        template_name = require_string(errors, repo_set.get("template"), f"{path}.template")
        if template_name and template_name not in repo_templates:
            error(errors, f"{path}.template references unknown template '{template_name}'")
            continue

        names = repo_set.get("names")
        name_template = repo_set.get("name_template")
        services = repo_set.get("services")
        description_template = repo_set.get("description_template")

        if names is None and (name_template is None or services is None):
            error(errors, f"{path} must define either names or (name_template + services)")
            continue

        if names is not None:
            name_list = require_list(errors, names, f"{path}.names")
            for idx, name in enumerate(name_list):
                name_str = require_string(errors, name, f"{path}.names[{idx}]")
                if name_str in seen_names:
                    error(errors, f"Duplicate repo name '{name_str}' in repo_sets")
                else:
                    seen_names.add(name_str)
                    expanded.append((name_str, repo_set))
            continue

        name_template_str = require_string(errors, name_template, f"{path}.name_template")
        service_list = require_list(errors, services, f"{path}.services")
        if "{service}" not in name_template_str:
            error(errors, f"{path}.name_template must include '{{service}}'")
        if description_template is not None:
            require_string(errors, description_template, f"{path}.description_template")
            if "{service}" not in description_template:
                error(errors, f"{path}.description_template must include '{{service}}'")

        for idx, service in enumerate(service_list):
            service_str = require_string(errors, service, f"{path}.services[{idx}]")
            if not service_str:
                continue
            name_str = name_template_str.replace("{service}", service_str)
            if name_str in seen_names:
                error(errors, f"Duplicate repo name '{name_str}' in repo_sets")
                continue
            seen_names.add(name_str)
            expanded.append((name_str, repo_set))

        overrides = repo_set.get("overrides")
        if overrides is not None:
            overrides_list = require_list(errors, overrides, f"{path}.overrides")
            for j, item in enumerate(overrides_list):
                item_path = f"{path}.overrides[{j}]"
                item_obj = require_dict(errors, item, item_path)
                name_value = item_obj.get("name")
                service_value = item_obj.get("service")
                if name_value is None and service_value is None:
                    error(errors, f"{item_path} must include 'name' or 'service'")
                if name_value is not None:
                    require_string(errors, name_value, f"{item_path}.name")
                if service_value is not None:
                    require_string(errors, service_value, f"{item_path}.service")
                if "overrides" not in item_obj:
                    error(errors, f"{item_path}.overrides is required")
                else:
                    if not isinstance(item_obj["overrides"], dict):
                        error(errors, f"{item_path}.overrides must be an object")

    if not expanded:
        warn(warnings, "No repositories expanded from repo_sets")

    return expanded


def validate_config(config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    patterns = require_dict(errors, config.get("patterns"), "patterns")
    repo_templates = require_dict(errors, config.get("repo_templates"), "repo_templates")
    repo_sets = require_list(errors, config.get("repo_sets"), "repo_sets")

    if errors:
        return errors, warnings

    for name, obj in patterns.items():
        if not isinstance(obj, dict):
            error(errors, f"patterns.{name} must be an object")
            continue
        validate_pattern(errors, name, obj)

    for name, obj in repo_templates.items():
        if not isinstance(obj, dict):
            error(errors, f"repo_templates.{name} must be an object")
            continue
        validate_repo_template(errors, name, obj, patterns)

    expanded = expand_repo_sets(errors, warnings, repo_sets, repo_templates)
    if not expanded:
        warn(warnings, "repo_sets did not generate any repos")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate fixture config.json")
    parser.add_argument(
        "--path",
        default="tests/fixtures/scenarios/config.json",
        help="Path to fixture config JSON",
    )
    args = parser.parse_args()

    config_path = Path(args.path)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON: {exc}", file=sys.stderr)
        return 1

    errors, warnings = validate_config(config)

    if warnings:
        for message in warnings:
            print(f"WARN: {message}")

    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        print(f"ERROR: Validation failed with {len(errors)} error(s)", file=sys.stderr)
        return 1

    print("[OK] config.json validated successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
