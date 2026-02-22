#!/usr/bin/env python3
"""
Call the Ollama API to generate a file. Runs inside Docker.

Usage:
    python scripts/ollama-generate.py \
        --model qwen3-coder:30b \
        --prompt .ai/ollama-prompts/013-B-fixture-extractor.md \
        --output tests/fixtures/fixture_extractor.py \
        [--context src/extractors/base.py ...] \
        [--ollama-url http://host.docker.internal:11434]
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.request


def call_ollama(model, messages, ollama_url, timeout=600):
    payload = {"model": model, "messages": messages, "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return result["message"]["content"]


def extract_code_block(text):
    """Return the last fenced code block, or the full text if none found."""
    blocks = re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True, help="Path to prompt markdown file")
    parser.add_argument("--output", required=True, help="File path to write")
    parser.add_argument("--context", action="append", default=[], metavar="FILE",
                        help="Read-only context files shown to the model (repeatable)")
    parser.add_argument("--ollama-url", default="http://host.docker.internal:11434")
    parser.add_argument("--raw", action="store_true",
                        help="Write full model response instead of extracting code block")
    args = parser.parse_args()

    prompt_path = pathlib.Path(args.prompt)
    if not prompt_path.exists():
        print(f"ERROR: Prompt file not found: {args.prompt}", file=sys.stderr)
        sys.exit(1)

    messages = []

    if args.context:
        parts = ["You are an expert Python developer. Here is the relevant existing code:\n"]
        for ctx in args.context:
            ctx_path = pathlib.Path(ctx)
            if not ctx_path.exists():
                print(f"ERROR: Context file not found: {ctx}", file=sys.stderr)
                sys.exit(1)
            lang = "python" if ctx.endswith(".py") else ""
            parts.append(f"### {ctx}\n```{lang}\n{ctx_path.read_text(encoding='utf-8')}\n```")
        messages.append({"role": "system", "content": "\n\n".join(parts)})

    messages.append({"role": "user", "content": prompt_path.read_text(encoding="utf-8")})

    print(f"  model  : {args.model}")
    print(f"  prompt : {args.prompt}")
    print(f"  output : {args.output}")
    for ctx in args.context:
        print(f"  context: {ctx}")
    print(f"  Calling Ollama... (may take a few minutes for large models)")

    try:
        response = call_ollama(args.model, messages, args.ollama_url)
    except Exception as e:
        print(f"ERROR: Ollama call failed: {e}", file=sys.stderr)
        sys.exit(1)

    content = response if args.raw else extract_code_block(response)

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"  Written {len(content)} chars -> {args.output}")


if __name__ == "__main__":
    main()
