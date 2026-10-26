"""Run the API agent.

  python API/main.py                      interactive chat, new session
  python API/main.py --session ID         continue a saved session
  python API/main.py "one message"        single message, then exit
  python API/main.py --scenario scenario.json --out results/api.json
"""

import argparse
import sys
from pathlib import Path

import truststore

# NetFree's CA fails Python 3.14's strict checks; verify TLS via the Windows cert store instead.
truststore.inject_into_ssl()

API_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(API_DIR.parent), str(API_DIR)]

from agent import Agent  # noqa: E402


def show(result: dict) -> None:
    print(f"\n{result['reply']}\n")
    print(f"  ({result['model_calls']} calls, tools={result['tools']}, "
          f"cache {result['cache_hit_pct']}%, ${result['cost_usd']:.4f}, {result['seconds']}s)\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="*")
    parser.add_argument("--session", help="session id to resume")
    parser.add_argument("--scenario", help="scenario.json to run end to end")
    parser.add_argument("--out", default="results/api.json")
    args = parser.parse_args()

    if args.scenario:
        from shared.scenario import run_scenario

        def run_session(prompts):
            agent = Agent()  # a new instance per session: only the disk carries state over
            return [agent.ask(p) for p in prompts]

        run_scenario(args.scenario, args.out, "api", run_session)
        return

    agent = Agent(session_id=args.session)
    if args.message:
        show(agent.ask(" ".join(args.message)))
        return
    print(f"session {agent.session_id} - empty line to quit")
    while text := input("> ").strip():
        show(agent.ask(text))


if __name__ == "__main__":
    main()
