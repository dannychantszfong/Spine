"""A runnable single agent wired to the four tools.

This is the smallest real thing you can build on spine: instantiate `Agent` with
a model and the four built-ins, then feed it a task. The loop, tool dispatch, and
provider call all come from the core — this file adds nothing but a `main`.

Usage:

    # litellm reads credentials from the environment. For Anthropic:
    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/minimal_agent.py "list the python files here and count their lines"

    # Any litellm-supported model works; override with --model:
    python examples/minimal_agent.py --model gpt-4o "summarize README.md"

The default model is Anthropic's Claude (the latest Opus). Swap freely — the
provider layer normalizes whichever you pick.
"""

from __future__ import annotations

import argparse

from spine import Agent, default_tools

DEFAULT_MODEL = "anthropic/claude-opus-4-8"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal spine agent.")
    parser.add_argument("task", help="The task for the agent to perform.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"litellm model id (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    agent = Agent(model=args.model, tools=default_tools())
    final = agent.run(args.task)

    print("\n=== agent finished ===")
    print(final)


if __name__ == "__main__":
    main()
