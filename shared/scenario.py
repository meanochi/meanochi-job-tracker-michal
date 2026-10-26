"""Scenario runner shared by API/main.py and SDK/main.py, so both are measured the same way.

Each run starts from a clean data directory (runs/<version>/), plays every session on a
new agent instance, runs the pass/fail checks (mostly on disk state), counts harness
lines of code, and writes the results JSON.
"""

import ast
import json
import os
import re
import shutil
import time
from pathlib import Path

from shared import jobs, preferences

ROOT = Path(__file__).resolve().parent.parent
HARNESS_PARTS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]
TOKEN_KEYS = ["input", "cache_read", "cache_write", "output", "model_calls", "cost_usd", "seconds"]


# --- checks -----------------------------------------------------------------

def _job(company: str) -> dict | None:
    return next((j for j in jobs.load_jobs() if company in j["company"].lower()), None)


def run_check(check: dict, turns: list[dict]) -> tuple[bool, str]:
    kind = check["type"]
    if kind == "job_count":
        n = len(jobs.load_jobs())
        return n == check["expect"], f"{n} applications in jobs.json"
    if kind == "job_status":
        job = _job(check["company"])
        status = job["status"] if job else None
        return status == check["expect"], f"status in jobs.json: {status}"
    if kind == "single_work_mode":
        # exactly one stored preference about work mode, and it is the newer one
        prefs = preferences.load_preferences()
        mode = {k: v for k, v in prefs.items() if re.search(r"hybrid|office|remote", v, re.I)}
        ok = len(mode) == 1 and check["must_include"] in next(iter(mode.values())).lower()
        return ok, f"work-mode preferences: {mode}"
    if kind == "tool_called":
        used = turns[check["turn"] - 1]["tools"]
        return check["tool"] in used, f"turn {check['turn']} tools: {used}"
    if kind == "reply_contains":
        reply = turns[check["turn"] - 1]["reply"].lower()
        missing = [w for w in check["all"] if w not in reply]
        return not missing, f"missing: {missing}" if missing else "all words found"
    raise ValueError(f"unknown check type {kind}")


# --- lines of code ----------------------------------------------------------

def _code_lines(path: Path) -> int:
    """Non-blank, non-comment lines, without docstrings."""
    source = path.read_text(encoding="utf-8")
    skip = set()
    for node in ast.walk(ast.parse(source)):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            skip.update(range(body[0].lineno, body[0].end_lineno + 1))
    return sum(1 for i, line in enumerate(source.splitlines(), 1)
               if i not in skip and line.strip() and not line.strip().startswith("#"))


def count_loc() -> dict:
    api = {p: _code_lines(ROOT / "API" / "harness" / f"{p}.py") for p in HARNESS_PARTS}
    sdk = dict.fromkeys(HARNESS_PARTS, 0)
    for f in (ROOT / "SDK").glob("*.py"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if "# replaces:" in line:
                marked = line.split("# replaces:", 1)[1]
                for p in HARNESS_PARTS:
                    if re.search(rf"\b{p}\.py\b", marked):
                        sdk[p] += 1
    api["total"], sdk["total"] = sum(api.values()), sum(sdk.values())
    return {"api": api, "sdk": sdk}


# --- runner -----------------------------------------------------------------

def run_scenario(scenario_path: str, out_path: str, version: str, run_session,
                 runs_dir: Path = ROOT / "runs") -> dict:
    """run_session(prompts) -> list of turn dicts; it must create a NEW agent each call."""
    scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
    data = Path(runs_dir) / version
    shutil.rmtree(data, ignore_errors=True)  # every run starts from a clean state
    os.environ["JOB_TRACKER_DIR"] = str(data)
    print(f"[scenario.py] {version}: clean data dir {data}")

    turns, t0 = [], time.perf_counter()
    for s, session in enumerate(scenario["sessions"], 1):
        print(f"[scenario.py] --- {session['name']} (new agent instance) ---")
        for prompt, result in zip(session["turns"], run_session(session["turns"])):
            turns.append({"turn": len(turns) + 1, "session": s, "prompt": prompt, **result})

    checks = []
    for c in scenario["checks"]:
        ok, detail = run_check(c, turns)
        checks.append({"id": c["id"], "passed": ok, "detail": detail})
        print(f"[scenario.py] {'PASS' if ok else 'FAIL'} {c['id']}: {detail}")

    totals = {k: round(sum(t.get(k, 0) for t in turns), 6) for k in TOKEN_KEYS}
    prompt_tokens = totals["input"] + totals["cache_read"] + totals["cache_write"]
    totals["cache_hit_pct"] = round(100 * totals["cache_read"] / prompt_tokens, 1) if prompt_tokens else 0.0
    totals["wall_seconds"] = round(time.perf_counter() - t0, 1)

    results = {
        "version": version,
        "scenario": scenario_path,
        "turns": turns,
        "totals": totals,
        "checks": checks,
        "checks_passed": f"{sum(c['passed'] for c in checks)}/{len(checks)}",
        "loc": count_loc(),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scenario.py] {results['checks_passed']} checks passed, ${totals['cost_usd']:.4f} -> {out_path}")
    return results
