"""SDK/ offline: tool wrappers and options. The Claude Code process itself is not started."""

import asyncio
import importlib.util
import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "SDK"))
import tools as sdk_tools  # noqa: E402  (SDK/tools.py)

_spec = importlib.util.spec_from_file_location("sdk_agent", ROOT / "SDK" / "agent.py")
sdk_agent = importlib.util.module_from_spec(_spec)  # API/agent.py is already "agent"
_spec.loader.exec_module(sdk_agent)

import agent as api_agent  # noqa: E402
from harness import tools as api_tools  # noqa: E402


def call(tool, **args):
    return asyncio.run(tool.handler(args))


def test_tool_results_and_errors():
    ok = call(sdk_tools.add_application, company="Wix", role="Dev", url="")
    assert ok == {"content": [{"type": "text", "text": "added: Wix | Dev | applied"}]}
    err = call(sdk_tools.update_status, company="Nope", status="offer")
    assert err["is_error"] is True and "no application" in err["content"][0]["text"]


def test_same_tools_model_and_effort_as_api():
    assert {t.name for t in sdk_tools.ALL} == {s["name"] for s in api_tools.SCHEMAS}
    assert (sdk_agent.MODEL, sdk_agent.EFFORT) == (api_agent.MODEL, api_agent.EFFORT)


def test_options_are_locked_down():
    o = sdk_agent.Agent().options
    assert o.strict_mcp_config is True
    assert o.tools == []  # no built-in Claude Code tools
    assert o.allowed_tools == sdk_tools.ALLOWED
    assert o.system_prompt == sdk_agent.SYSTEM_PROMPT
    assert o.setting_sources == ["project"]


def test_memory_file_is_rendered_from_preferences(offline):
    call(sdk_tools.save_preference, key="work_mode", value="hybrid only")
    sdk_agent.Agent()
    assert "- work_mode: hybrid only" in (offline / "CLAUDE.md").read_text(encoding="utf-8")
