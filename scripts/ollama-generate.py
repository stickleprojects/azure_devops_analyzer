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
import time
import urllib.request


def call_ollama(model, messages, ollama_url, num_ctx=8192, timeout=600):
    payload = {"model": model, "messages": messages, "stream": True, "options": {"num_ctx": num_ctx}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    content_parts = []
    token_count = 0
    start_time = time.time()
    stats = {}
    use_tty = sys.stdout.isatty()

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line = raw_line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("done"):
                stats = chunk
                break
            token = chunk.get("message", {}).get("content", "")
            if token:
                content_parts.append(token)
                token_count += 1
                elapsed = time.time() - start_time
                tok_per_sec = token_count / elapsed if elapsed > 0 else 0.0
                if use_tty:
                    print(
                        f"\r  Generating: {token_count} tokens ({tok_per_sec:.1f} tok/s)...",
                        end="",
                        flush=True,
                    )
                elif token_count % 100 == 0:
                    print(f"  ... {token_count} tokens ({tok_per_sec:.1f} tok/s)", flush=True)

    if use_tty:
        print()  # end the \r progress line

    if stats:
        eval_count = stats.get("eval_count", token_count)
        eval_dur_ns = stats.get("eval_duration", 0)
        prompt_count = stats.get("prompt_eval_count", 0)
        prompt_dur_ns = stats.get("prompt_eval_duration", 0)
        total_dur_ns = stats.get("total_duration", 0)

        gen_tps = eval_count / (eval_dur_ns / 1e9) if eval_dur_ns > 0 else 0.0
        prompt_tps = prompt_count / (prompt_dur_ns / 1e9) if prompt_dur_ns > 0 else 0.0
        print(
            f"  Perf: prompt={prompt_count} tok @ {prompt_tps:.1f} tok/s | "
            f"gen={eval_count} tok @ {gen_tps:.1f} tok/s | "
            f"total={total_dur_ns / 1e9:.1f}s"
        )

    return "".join(content_parts)


def extract_code_block(text):
    """Return the largest fenced code block, or the full text if none found.
    
    Prefers the largest block to avoid extracting usage examples instead of implementations.
    """
    blocks = re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    if blocks:
        # Prefer largest block to avoid usage examples
        largest = max(blocks, key=len)
        if len(largest.strip()) > 50:  # Minimum viable code
            return largest.strip()
        # If all blocks are tiny, fall back to last one (original behavior)
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
    parser.add_argument("--num-ctx", type=int, default=8192,
                        help="Context window size (default: 8192; smaller = less VRAM)")
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
    print(f"  ctx    : {args.num_ctx} tokens")
    print(f"  prompt : {args.prompt}")
    print(f"  output : {args.output}")
    for ctx in args.context:
        print(f"  context: {ctx}")
    print(f"  Calling Ollama (streaming)...")

    t0 = time.time()
    try:
        response = call_ollama(args.model, messages, args.ollama_url, num_ctx=args.num_ctx)
    except Exception as e:
        print(f"ERROR: Ollama call failed: {e}", file=sys.stderr)
        sys.exit(1)
    elapsed = time.time() - t0
    print(f"  Wall time: {elapsed:.1f}s")

    content = response if args.raw else extract_code_block(response)

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"  Written {len(content)} chars -> {args.output}")


if __name__ == "__main__":
    main()
