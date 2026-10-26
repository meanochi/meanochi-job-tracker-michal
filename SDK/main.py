"""Run the SDK agent (bills your Claude Code login, not an API key).

  python SDK/main.py                      interactive chat, new session
  python SDK/main.py --session ID         continue a saved session
  python SDK/main.py "one message"        single message, then exit
  python SDK/main.py --scenario scenario.json --out results/sdk.json
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

SDK_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(SDK_DIR.parent), str(SDK_DIR)]

import truststore  # noqa: E402

# NetFree's CA fails Python 3.14's strict checks (needed by fetch_job_posting's process).
truststore.inject_into_ssl()

from agent import Agent  # noqa: E402


def show(result: dict) -> None:
    print(f"\n{result['reply']}\n")
    print(f"  ({result['model_calls']} calls, tools={result['tools']}, "
          f"cache {result['cache_hit_pct']}%, ${result['cost_usd']:.4f}, {result['seconds']}s)\n")


def run_session(prompts: list[str]) -> list[dict]:
    async def go():
        async with Agent() as agent:  # a new instance per session: only the disk carries state over
            return [await agent.ask(p) for p in prompts]
    return asyncio.run(go())


async def run(args) -> None:
    async with Agent(session_id=args.session) as agent:
        if args.message:
            show(await agent.ask(" ".join(args.message)))
        else:
            print("empty line to quit")
            while text := input("> ").strip():
                show(await agent.ask(text))
        print(f"session id: {agent.session_id}")


def main() -> None:
    if os.environ.pop("ANTHROPIC_API_KEY", None):
        print("[main.py] ANTHROPIC_API_KEY removed for this run, so billing goes to your Claude login")
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="*")
    parser.add_argument("--session", help="session id to resume")
    parser.add_argument("--scenario", help="scenario.json to run end to end")
    parser.add_argument("--out", default="results/sdk.json")
    args = parser.parse_args()
    if args.scenario:
        from shared.scenario import run_scenario
        run_scenario(args.scenario, args.out, "sdk", run_session)
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
