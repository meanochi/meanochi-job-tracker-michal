"""One test group per harness file in API/harness/."""

import json

from conftest import FakeClient, response, text, thinking, tool, without_cache_control
from harness import caching, compaction, context, loop, tokens, tools
from harness.history import History
from harness.tokens import TokenTracker
from shared import jobs, preferences


# --- tools.py ---------------------------------------------------------------

def test_tool_success_and_errors_go_back_as_results():
    ok = tools.run_tool("add_application", {"company": "Wix", "role": "Dev"}, "t1")
    assert ok == {"type": "tool_result", "tool_use_id": "t1", "content": "added: Wix | Dev | applied"}

    for name, args, msg in [
        ("update_status", {"company": "Nope", "status": "offer"}, "no application"),
        ("add_application", {"company": "Wix"}, "bad arguments"),
        ("no_such_tool", {}, "unknown tool"),
    ]:
        err = tools.run_tool(name, args, "t2")
        assert err["is_error"] is True and msg in err["content"]


def test_long_tool_output_is_capped(monkeypatch):
    monkeypatch.setitem(tools.FUNCTIONS, "search_applications", lambda **_: "x" * 10_000)
    out = tools.run_tool("search_applications", {}, "t")["content"]
    assert len(out) < tools.MAX_RESULT_CHARS + 20 and out.endswith("[truncated]")


def test_every_schema_has_a_function():
    assert {s["name"] for s in tools.SCHEMAS} == set(tools.FUNCTIONS)


# --- history.py -------------------------------------------------------------

def test_history_is_append_only_and_survives_reload(tmp_path):
    path = tmp_path / "s.jsonl"
    h = History(path)
    h.set_system([{"type": "text", "text": "sys"}])
    h.append({"role": "user", "content": "hi"})
    h.append({"role": "assistant", "content": [{"type": "text", "text": "hello"}]})
    lines_before = path.read_text(encoding="utf-8").splitlines()

    h.add_compaction("they said hi")
    h.append({"role": "user", "content": "again"})
    assert path.read_text(encoding="utf-8").splitlines()[:3] == lines_before  # old lines untouched

    reloaded = History(path)
    assert reloaded.system == [{"type": "text", "text": "sys"}]
    msgs = reloaded.messages()
    assert len(msgs) == 2 and "they said hi" in msgs[0]["content"][0]["text"]
    assert msgs[1] == {"role": "user", "content": "again"}


# --- memory.py + context.py -------------------------------------------------

def test_system_prompt_is_static():
    before = context.build_system()
    preferences.save_preference("work_mode", "hybrid only")
    jobs.add_application("Wix", "Dev")
    after = context.build_system()
    assert after == before  # memory never changes it, so it stays cached across sessions
    assert "hybrid only" not in after[0]["text"] and "Wix" not in after[0]["text"]


def test_preferences_only_in_first_turn_of_session():
    preferences.save_preference("work_mode", "hybrid only")
    first = context.build_user_turn("hi", first_in_session=True)["content"]
    later = context.build_user_turn("hi again")["content"]
    assert "<memory>" in first[0]["text"] and "work_mode: hybrid only" in first[0]["text"]
    assert len(first) == 3 and first[-1]["text"] == "hi"
    assert not any("<memory>" in b["text"] for b in later)


def test_user_turn_gets_only_mentioned_companies():
    jobs.add_application("Wix", "Dev")
    jobs.add_application("Monday", "QA")
    turn = context.build_user_turn("any news from wix?")
    ctx, user = turn["content"]
    assert "Tracked applications: 2 (applied 2)." in ctx["text"]
    assert "Wix | Dev | applied" in ctx["text"] and "Monday" not in ctx["text"]
    assert user["text"] == "any news from wix?"


# --- caching.py -------------------------------------------------------------

def test_cache_breakpoints_on_copies_only():
    system = [{"type": "text", "text": "sys"}]
    messages = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"},
                {"role": "user", "content": [{"type": "text", "text": "c"}]}]
    original = json.dumps([system, messages])

    s, m = caching.apply(system, messages)
    assert s[-1]["cache_control"] == {"type": "ephemeral"}
    assert m[-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert json.dumps([system, messages]) == original  # inputs not mutated
    assert json.dumps([s, m]).count("cache_control") == 2  # within the API limit of 4


# --- tokens.py --------------------------------------------------------------

def test_cost_and_turn_totals():
    t = TokenTracker()
    t.start_turn()
    t.record(response("end_turn", input=1000, output=100, cache_read=9000, cache_write=0).usage)
    t.add_tools(["search_applications"])
    turn = t.end_turn()
    # 1000*$4 + 9000*$0.20 + 100*$20, per million
    assert turn["cost_usd"] == round((4000 + 1800 + 2000) / 1e6, 6)
    assert turn["cache_hit_pct"] == 90.0
    assert turn["model_calls"] == 1 and turn["tools"] == ["search_applications"]
    assert t.last_context_tokens == 10_100


def test_prices_match_opus_5_5():
    assert tokens.PRICES == {"input": 4.0, "cache_write": 5.0, "cache_read": 0.2, "output": 20.0}


# --- loop.py ----------------------------------------------------------------

def make_call(client, tracker):
    def call(messages):
        r = client.messages.create(messages=messages)
        tracker.record(r.usage)
        return r
    return call


def run(client, tmp_path):
    h, t = History(tmp_path / "loop.jsonl"), TokenTracker()
    h.append({"role": "user", "content": "go"})
    t.start_turn()
    reply = loop.run_turn(make_call(client, t), h, t)
    return reply, h, t.end_turn()


def test_parallel_tool_results_return_in_one_message(tmp_path):
    client = FakeClient(
        response("tool_use", thinking("s1"),
                 tool("a", "add_application", company="Wix", role="Dev"),
                 tool("b", "update_status", company="Ghost", status="offer")),
        response("end_turn", text("done")),
    )
    reply, h, turn = run(client, tmp_path)
    assert reply == "done" and turn["model_calls"] == 2
    results = client.requests[1]["messages"][-1]
    assert results["role"] == "user" and [r["tool_use_id"] for r in results["content"]] == ["a", "b"]
    assert "is_error" not in results["content"][0] and results["content"][1]["is_error"] is True
    # the assistant turn went back unchanged, thinking signature included
    assert client.requests[1]["messages"][1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "s1"}


def test_cut_off_tool_use_still_gets_a_result(tmp_path):
    client = FakeClient(response("max_tokens", tool("a", "search_applications")))
    reply, h, _ = run(client, tmp_path)
    last = h.messages()[-1]
    assert last["content"][0]["tool_use_id"] == "a" and last["content"][0]["is_error"] is True


def test_runaway_loop_is_stopped(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "MAX_MODEL_CALLS", 3)
    client = FakeClient(*[response("tool_use", tool(f"t{i}", "search_applications")) for i in range(3)])
    reply, _, turn = run(client, tmp_path)
    assert "stopped" in reply and turn["model_calls"] == 3


# --- compaction.py ----------------------------------------------------------

def test_compaction_threshold():
    assert not compaction.should_compact(999, 1000)
    assert compaction.should_compact(1001, 1000)


def test_compaction_replaces_whole_history_with_summary(tmp_path):
    h = History(tmp_path / "c.jsonl")
    for i in range(3):
        h.append({"role": "user", "content": f"q{i}"})
        h.append({"role": "assistant", "content": [{"type": "text", "text": f"a{i}"}]})
    client = FakeClient(response("end_turn", text("user likes hybrid")))
    compaction.compact(lambda m: client.messages.create(messages=m), h)

    sent = client.requests[0]["messages"]
    assert len(sent) == 7 and "Summarize" in sent[-1]["content"][0]["text"]
    msgs = h.messages()
    assert len(msgs) == 1 and "user likes hybrid" in msgs[0]["content"][0]["text"]
    assert without_cache_control(msgs) == msgs
