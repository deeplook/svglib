#!/usr/bin/env python3
"""Fail CI if a security-relevant package resolves below its minimum safe version.

Stdlib only; runs on Python 3.10+ (CPython and PyPy).

Sources checked (all together; the run fails if ANY source shows a version
below the minimum):

  lock  Every ``[[package]]`` entry in ``uv.lock`` (direct and transitive, all
        Python-version/platform forks; if a package is locked at several
        versions, each one is checked). Parsed with ``tomllib`` on Python
        3.11+, otherwise (Python 3.10) with a small built-in fallback parser
        that reads the ``name``/``version`` keys of each ``[[package]]`` table.
  env   The distributions installed in the environment of the interpreter
        running this script (``importlib.metadata``), e.g. the project's
        ``.venv`` when started via ``uv run --no-sync python ...``, or the
        setup-python interpreter when started via ``python ...``. This catches
        packages installed outside the lock (``pip install -e .[test]``) and
        tools such as pip itself. Skip with ``--no-env``.
  tool  The ``uv`` executable on PATH (or ``$UV``, which ``uv run`` sets):
        ``uv --version`` is compared against the uv minimum. uv not found
        means absent (pass).

Rules: a package that is absent passes; a version >= minimum passes; a version
< minimum fails. A version string that cannot be parsed as PEP 440 also fails
(conservative: we cannot prove it is safe).

Version comparison follows PEP 440 ordering: epoch, release segments compared
numerically with missing trailing segments treated as 0 (so 26.10 > 26.2.2 and
2026.10.19 > 2026.7.22), then dev < pre (a < b < rc) < final < post. Local
labels (``+abc``) are ignored. A pre-release or dev build of the minimum (e.g.
26.2.2rc1) is therefore below 26.2.2 and fails; 26.2.2.post1 passes.

Package names are normalized per PEP 503 (lowercase, runs of ``-_.`` -> ``-``).

Testing hooks: ``--lock PATH`` (use another lockfile), ``--uv-version X``
(or env ``CHECK_MIN_VERSIONS_UV_VERSION``) to fake the uv binary version.

Exit codes: 0 all pass, 1 at least one failure, 2 usage/IO error.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Minimum safe versions (security advisories of 2026-10-21/22).
MINIMUMS = {
    "certifi": "2026.10.19",
    "pip": "26.2.2",
    "uv": "0.13.4",
    "sigstore": "4.5.1",
    "conda": "26.9.4",
    "pixi": "0.82.1",
}


def normalize(name: str) -> str:
    """PEP 503 name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


_VERSION_RE = re.compile(
    r"""
    ^\s*v?
    (?:(?P<epoch>[0-9]+)!)?
    (?P<release>[0-9]+(?:\.[0-9]+)*)
    (?:[-_.]?(?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)[-_.]?(?P<pre_n>[0-9]+)?)?
    (?:(?:-(?P<post_n1>[0-9]+))|(?:[-_.]?(?P<post_l>post|rev|r)[-_.]?(?P<post_n2>[0-9]+)?))?
    (?:[-_.]?(?P<dev_l>dev)[-_.]?(?P<dev_n>[0-9]+)?)?
    (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

_PRE_RANK = {
    "a": 0,
    "alpha": 0,
    "b": 1,
    "beta": 1,
    "c": 2,
    "rc": 2,
    "pre": 2,
    "preview": 2,
}
_INF = float("inf")


def version_key(version: str):
    """Return a sortable key implementing PEP 440 ordering, or None if invalid."""
    m = _VERSION_RE.match(version)
    if not m:
        return None
    epoch = int(m.group("epoch") or 0)
    release = [int(x) for x in m.group("release").split(".")]
    while len(release) > 1 and release[-1] == 0:  # 1.0 == 1.0.0
        release.pop()
    has_pre = m.group("pre_l") is not None
    has_post = m.group("post_n1") is not None or m.group("post_l") is not None
    has_dev = m.group("dev_l") is not None
    if has_pre:
        pre = (_PRE_RANK[m.group("pre_l").lower()], int(m.group("pre_n") or 0))
    elif has_dev and not has_post:
        pre = (-_INF, 0)  # 1.0.dev0 sorts before 1.0a0
    else:
        pre = (_INF, 0)  # final release sorts after its pre-releases
    if has_post:
        post = (int(m.group("post_n1") or m.group("post_n2") or 0),)
        post = (1,) + post
    else:
        post = (0, 0)
    dev = (int(m.group("dev_n") or 0),) if has_dev else (_INF,)
    return (epoch, tuple(release), pre, post, dev)


def compare(found: str, minimum: str) -> str:
    """'pass', 'FAIL' (below minimum) or 'FAIL(unparseable)'."""
    kf, km = version_key(found), version_key(minimum)
    if km is None:
        raise ValueError(f"invalid minimum version {minimum!r}")
    if kf is None:
        return "FAIL(unparseable)"
    # Release tuples of different length: pad with zeros for comparison.
    rf, rm = list(kf[1]), list(km[1])
    n = max(len(rf), len(rm))
    rf += [0] * (n - len(rf))
    rm += [0] * (n - len(rm))
    kf = (kf[0], tuple(rf)) + kf[2:]
    km = (km[0], tuple(rm)) + km[2:]
    return "pass" if kf >= km else "FAIL"


# ---------------------------------------------------------------- sources


def _parse_lock_fallback(text: str):
    """Minimal uv.lock reader for Python < 3.11: name/version of [[package]]."""
    packages = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            if current is not None:
                packages.append(current)
            current = {} if line == "[[package]]" else None
            continue
        if current is None:
            continue
        m = re.match(r'^(name|version)\s*=\s*"([^"]*)"\s*$', line)
        if m and m.group(1) not in current:
            current[m.group(1)] = m.group(2)
    if current is not None:
        packages.append(current)
    return packages


def read_lock(path: Path):
    """Return ({name: {versions}}, parser name, package count) for a uv.lock."""
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        parser = "fallback"
        packages = _parse_lock_fallback(text)
    else:
        parser = "tomllib"
        packages = tomllib.loads(text).get("package", [])
    found = {}
    for pkg in packages:
        name, version = pkg.get("name"), pkg.get("version")
        if name and version:
            found.setdefault(normalize(name), set()).add(version)
    return found, parser, len(packages)


def read_env():
    """Return {name: {versions}} for the running interpreter's environment."""
    try:
        from importlib import metadata
    except ImportError:  # pragma: no cover
        return None
    found = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") if dist.metadata else None
        if name and dist.version:
            found.setdefault(normalize(name), set()).add(dist.version)
    return found


def read_uv_tool(override: str | None):
    """Return ({"uv": {version}}, note) for the uv executable, if any."""
    if override:
        return {"uv": {override}}, f"override {override}"
    exe = os.environ.get("UV") or shutil.which("uv")
    if not exe:
        return {}, "uv not found on PATH"
    try:
        out = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=30, check=True
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return {"uv": {f"<error: {exc}>"}}, f"{exe}: failed to run"
    m = re.match(r"^uv\s+(\S+)", out)
    return {"uv": {m.group(1) if m else out}}, f"{exe}: {out}"


# ---------------------------------------------------------------- main


def main(argv=None) -> int:
    """Run the check; return the process exit code."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--lock",
        default="uv.lock",
        help="path to uv.lock (default: ./uv.lock)",
    )
    ap.add_argument(
        "--no-env",
        action="store_true",
        help="skip the installed-environment source",
    )
    ap.add_argument(
        "--uv-version",
        default=os.environ.get("CHECK_MIN_VERSIONS_UV_VERSION"),
        help="pretend `uv --version` reports this (testing)",
    )
    args = ap.parse_args(argv)

    sources = {}  # source -> {pkg: {versions}}
    notes = []

    lock_path = Path(args.lock)
    if lock_path.is_file():
        try:
            lock, parser, count = read_lock(lock_path)
        except (OSError, ValueError) as exc:  # malformed lock: error, not pass
            print(f"ERROR: cannot parse {lock_path}: {exc}", file=sys.stderr)
            return 2
        sources["lock"] = lock
        notes.append(f"lock: {lock_path} ({count} packages, parser={parser})")
    else:
        notes.append(f"lock: {lock_path} not found, skipped")

    if args.no_env:
        notes.append("env: skipped (--no-env)")
    else:
        env = read_env()
        if env is None:
            notes.append("env: importlib.metadata unavailable, skipped")
        else:
            sources["env"] = env
            pyver = sys.version.split()[0]
            notes.append(f"env: {sys.executable} (Python {pyver}, prefix {sys.prefix})")

    tool, tool_note = read_uv_tool(args.uv_version)
    sources["tool"] = tool
    notes.append(f"tool: {tool_note}")

    print("Minimum safe version check")
    for n in notes:
        print(f"  {n}")
    print()
    row = "{:<10} {:<11} {:<6} {:<8} {:<30} {}"
    header = row.format(
        "package",
        "minimum",
        "source",
        "status",
        "version(s)",
        "result",
    )
    print(header)
    print("-" * len(header))

    failures = []
    for pkg, minimum in MINIMUMS.items():
        key = normalize(pkg)
        for src, data in sources.items():
            if src == "tool" and key != "uv":
                continue
            versions = sorted(data.get(key, ()))
            if not versions:
                print(row.format(pkg, minimum, src, "absent", "-", "pass"))
                continue
            results = []
            for v in versions:
                r = compare(v, minimum)
                results.append(f"{v}:{r}")
                if r != "pass":
                    failures.append((pkg, v, minimum, src, r))
            ok = all(x.endswith(":pass") for x in results)
            shown = ", ".join(versions)
            print(
                row.format(
                    pkg,
                    minimum,
                    src,
                    "present",
                    shown,
                    "pass" if ok else "FAIL",
                )
            )

    print()
    if failures:
        for pkg, v, minimum, src, r in failures:
            why = "is not a valid version" if "unparseable" in r else "is below minimum"
            print(f"FAIL: {pkg} {v} ({src}) {why} {minimum}")
        print(f"{len(failures)} failure(s).")
        return 1
    print("OK: no package below its minimum safe version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
