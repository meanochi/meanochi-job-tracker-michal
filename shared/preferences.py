"""User preferences that persist between sessions - plain Python, no AI.

Stored as preferences.json next to jobs.json. One value per key, so a newer
statement on the same topic replaces the old one (that is how contradictions resolve).
"""

import json

from shared.jobs import ToolError, data_dir


def _path():
    return data_dir() / "preferences.json"


def load_preferences() -> dict[str, str]:
    path = _path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_preference(key: str, value: str) -> str:
    key = key.strip().lower().replace(" ", "_")
    value = value.strip()
    if not key or not value:
        raise ToolError("key and value are required")
    prefs = load_preferences()
    old = prefs.get(key)
    prefs[key] = value
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prefs, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return f"saved: {key} = {value}" + (f" (was: {old})" if old is not None else "")
