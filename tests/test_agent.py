"""End to end: two sessions on fresh Agent instances, state carried only by the disk."""

import json

from agent import EFFORT, MODEL, Agent
from conftest import FakeClient, response, text, thinking, tool, without_cache_control


def test_two_sessions_memory_and_contradiction(offline):
    # Session 1: add an application and save "hybrid only".
    c1 = FakeClient(
        response("tool_use", thinking(),
                 tool("a", "add_application", company="Wix", role="Backend Developer"),
                 tool("b", "save_preference", key="work_mode", value="hybrid only")),
        response("end_turn", text("Saved.")),
        response("tool_use", tool("c", "update_status", company="Wix", status="interview")),
        response("end_turn", text("Updated.")),
    )
    s1 = Agent(client=c1, session_id="one")
    t1 = s1.ask("I applied to Wix as Backend Developer. I only want hybrid jobs.")
    s1.ask("Wix invited me to an interview")
    assert t1["model_calls"] == 2 and t1["tools"] == ["add_application", "save_preference"]

    req = c1.requests[0]
    assert req["model"] == MODEL and req["output_config"] == {"effort": EFFORT}
    # within a session every request extends the previous one (append-only prefix)
    for prev, nxt in zip(c1.requests, c1.requests[1:]):
        assert without_cache_control(nxt["system"]) == without_cache_control(prev["system"])
        p = without_cache_control(prev["messages"])
        assert without_cache_control(nxt["messages"])[:len(p)] == p

    # Session 2: brand-new Agent; memory comes from disk, then the contradiction.
    c2 = FakeClient(
        response("tool_use", tool("d", "save_preference", key="work_mode", value="hybrid or full office")),
        response("end_turn", text("Noted.")),
    )
    s2 = Agent(client=c2, session_id="two")
    s2.ask("Actually a full office job is fine too. How is Wix going?")

    first = c2.requests[0]
    memory_block, context_block = first["messages"][0]["content"][:2]
    assert "work_mode: hybrid only" in memory_block["text"]                             # recalled
    assert "Wix | Backend Developer | interview" in context_block["text"]
    # same system prompt in both sessions -> the tools + system prefix is cacheable across sessions
    assert first["system"] == c1.requests[0]["system"]
    # memory is sent once per session, not with every message
    assert "<memory>" not in json.dumps(c2.requests[-1]["messages"][-1])
    prefs = json.loads((offline / "preferences.json").read_text(encoding="utf-8"))
    assert prefs == {"work_mode": "hybrid or full office"}                              # overridden
    saved_jobs = json.loads((offline / "jobs.json").read_text(encoding="utf-8"))
    assert [(j["company"], j["status"]) for j in saved_jobs] == [("Wix", "interview")]


def test_resumed_session_sends_identical_prefix(offline):
    c1 = FakeClient(response("end_turn", text("hi")))
    Agent(client=c1, session_id="r").ask("hello")

    # a preference saved elsewhere must NOT change a resumed session's frozen system prompt
    from shared import preferences
    preferences.save_preference("location", "Tel Aviv")

    c2 = FakeClient(response("end_turn", text("again")))
    Agent(client=c2, session_id="r").ask("hello again")
    before, after = c1.requests[0], c2.requests[0]
    assert after["system"] == before["system"]
    n = len(before["messages"])
    assert without_cache_control(after["messages"][:n]) == without_cache_control(before["messages"])


def test_compaction_runs_before_the_turn_past_threshold(offline):
    client = FakeClient(
        response("end_turn", text("first"), input=5000),
        response("end_turn", text("SUMMARY: said hello")),   # compaction call
        response("end_turn", text("second")),
    )
    agent = Agent(client=client, session_id="c", compact_threshold=1000)
    agent.ask("hello")
    turn = agent.ask("and now?")
    assert turn["model_calls"] == 2  # summary + answer, both counted
    last = client.requests[-1]["messages"]
    assert len(last) == 2 and "SUMMARY: said hello" in last[0]["content"][0]["text"]
