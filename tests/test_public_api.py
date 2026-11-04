"""Snapshot of the importable surface of the svglib package.

Every name that `svglib`, `svglib.svglib`, `svglib.utils` and `svglib.fonts`
expose today may be imported by user code, so it must not disappear or change
its signature by accident, e.g. while modules are split up. If a change is
intended, regenerate the snapshot and review the diff:

    uv run python -m tests.test_public_api --update
"""

import inspect
import json
import sys
import types
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

SNAPSHOT = Path(__file__).with_name("public_api.json")
MODULES = ["svglib", "svglib.svglib", "svglib.utils", "svglib.fonts"]
CONSTANT_TYPES = (bool, int, float, str, bytes, tuple, frozenset, type(None))


def parameters(obj: Any) -> str:
    """Parameter names and kinds; annotations vary between Python versions."""
    try:
        params = inspect.signature(obj).parameters.values()
    except (TypeError, ValueError):
        return "(?)"
    return "(" + ", ".join(f"{p.kind.name}:{p.name}" for p in params) + ")"


def describe(obj: Any) -> str:
    """Return a stable description of an object, independent of the Python version.

    Only objects defined by svglib itself are described in detail; imported
    names (from the standard library, typing, ReportLab) and type aliases look
    different on different Python versions and are just recorded as present.
    """
    own = (getattr(obj, "__module__", "") or "").startswith("svglib")
    if own and inspect.isclass(obj):
        return f"class{parameters(obj)}"
    if own and callable(obj):
        return f"callable{parameters(obj)}"
    if isinstance(obj, frozenset):
        return f"constant frozenset({sorted(obj)!r})"
    if isinstance(obj, CONSTANT_TYPES):
        return f"constant {obj!r}"
    return "external"


def class_members(cls: type) -> list[str]:
    """Names defined by the class itself, private ones included."""
    return sorted(n for n in vars(cls) if not (n.startswith("__") and n.endswith("__")))


def snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for modname in MODULES:
        module = import_module(modname)
        entries: dict[str, Any] = {}
        for name, obj in sorted(vars(module).items()):
            if name.startswith("__") or isinstance(obj, types.ModuleType):
                continue
            entry: dict[str, Any] = {"what": describe(obj)}
            own = getattr(obj, "__module__", "") or ""
            if inspect.isclass(obj) and own.startswith("svglib"):
                entry["members"] = class_members(obj)
                entry["bases"] = [b.__name__ for b in obj.__bases__]
            entries[name] = entry
        result[modname] = entries
    return result


@pytest.mark.parametrize("modname", MODULES)
def test_public_api_is_unchanged(modname: str) -> None:
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))[modname]
    actual = snapshot()[modname]
    missing = sorted(set(expected) - set(actual))
    assert not missing, f"names removed from {modname}: {missing}"
    changed = {
        n: (expected[n], actual[n]) for n in expected if expected[n] != actual[n]
    }
    assert not changed, f"names changed in {modname}: {changed}"
    # New names are allowed but must be recorded deliberately.
    added = sorted(set(actual) - set(expected))
    assert not added, f"names added to {modname} (run with --update): {added}"


if __name__ == "__main__":
    if "--update" not in sys.argv:
        sys.exit(__doc__)
    SNAPSHOT.write_text(
        json.dumps(snapshot(), indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {SNAPSHOT}")
