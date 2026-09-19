#!/usr/bin/env python3
"""Explicit Supervisor GitHub bridge sync. No daemon, no cron, one push per publish."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

AGENT_LAB = Path(__file__).resolve().parents[1]
if str(AGENT_LAB) not in sys.path:
    sys.path.insert(0, str(AGENT_LAB))

from supervisor.engine.sync_policy import is_publish_allowed, is_secret_path

BRIDGE_DIR = AGENT_LAB / ".github-bridge"
CLEAN_PREFIX = "clean"
REMOTE_NAME = "origin"
DEFAULT_REMOTE = os.environ.get("EVE_AGENT_LAB_REMOTE", "")


class SyncError(Exception):
    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Never dump tokens in our own output; child git/gh may still use env.
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=env)
    if check and result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        redacted = _redact(err)
        raise SyncError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{redacted}", result.returncode)
    return result


def _redact(text: str) -> str:
    out = []
    for line in text.splitlines():
        lower = line.lower()
        if any(k in lower for k in ("token", "gho_", "ghp_", "ghu_", "password", "secret", "authorization:")):
            out.append("[redacted]")
        else:
            out.append(line)
    return "\n".join(out)


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in AGENT_LAB.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(AGENT_LAB).as_posix()
        if rel.startswith(".github-bridge/"):
            continue
        ok, _reason = is_publish_allowed(rel)
        if ok and not is_secret_path(path):
            files.append(path)
    return sorted(files)


def materialize_bridge() -> list[str]:
    staged: list[str] = []
    dest_root = BRIDGE_DIR / CLEAN_PREFIX
    if BRIDGE_DIR.exists() and (BRIDGE_DIR / ".git").exists() is False and any(BRIDGE_DIR.iterdir()):
        raise SyncError(f"{BRIDGE_DIR} exists and is not a git repo")
    dest_root.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    wanted: set[str] = set()
    for src in iter_source_files():
        rel = src.relative_to(AGENT_LAB).as_posix()
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        item = f"{CLEAN_PREFIX}/{rel}"
        staged.append(item)
        wanted.add(item)
    current = AGENT_LAB / "supervisor" / "CURRENT.json"
    policy = AGENT_LAB / "LOOP_POLICY.md"
    if current.exists():
        shutil.copy2(current, dest_root / "CURRENT.json")
        wanted.add(f"{CLEAN_PREFIX}/CURRENT.json")
        staged.append(f"{CLEAN_PREFIX}/CURRENT.json")
    if policy.exists():
        shutil.copy2(policy, dest_root / "LOOP_POLICY.md")
        wanted.add(f"{CLEAN_PREFIX}/LOOP_POLICY.md")
        staged.append(f"{CLEAN_PREFIX}/LOOP_POLICY.md")
    if dest_root.exists():
        for existing in dest_root.rglob("*"):
            if not existing.is_file():
                continue
            rel = existing.relative_to(dest_root).as_posix()
            item = f"{CLEAN_PREFIX}/{rel}"
            if item not in wanted:
                existing.unlink()
    gitignore = BRIDGE_DIR / ".gitignore"
    gitignore.write_text("*.env\n*.pem\n*.key\nid_rsa\nid_ed25519\n__pycache__/\n*.pyc\n", encoding="utf-8")
    return sorted(set(staged))


def ensure_repo() -> None:
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    if not (BRIDGE_DIR / ".git").exists():
        run(["git", "init", "-b", "main"], cwd=BRIDGE_DIR)
        run(["git", "config", "user.name", "CLEAN VI Migration Agent Lab"], cwd=BRIDGE_DIR)
        run(["git", "config", "user.email", "agent-lab@users.noreply.github.com"], cwd=BRIDGE_DIR)
        # local only — do not touch global git config


def git_status_porcelain() -> str:
    return run(["git", "status", "--porcelain"], cwd=BRIDGE_DIR, check=True).stdout


def cmd_status() -> int:
    files = [p.relative_to(AGENT_LAB).as_posix() for p in iter_source_files()]
    print("AGENT_LAB", AGENT_LAB)
    print("BRIDGE_DIR", BRIDGE_DIR)
    print("PUBLISH_CANDIDATES", len(files))
    for rel in files:
        print(" ", rel)
    if (BRIDGE_DIR / ".git").exists():
        remotes = run(["git", "remote", "-v"], cwd=BRIDGE_DIR, check=False).stdout.strip()
        print("REMOTES")
        print(remotes or "(none)")
        print("GIT_STATUS")
        print(git_status_porcelain() or "(clean)")
    else:
        print("BRIDGE_GIT=uninitialized")
    return 0


def cmd_publish() -> int:
    ensure_repo()
    staged = materialize_bridge()
    print("FILES_TO_COMMIT")
    for item in staged:
        print(" ", item)
    run(["git", "add", "--", "clean", ".gitignore"], cwd=BRIDGE_DIR)
    porcelain = git_status_porcelain()
    print("GIT_STATUS_STAGED")
    print(porcelain or "(no changes)")
    if not porcelain.strip():
        print("PUBLISH=NO_CHANGES")
        return 0
    run(["git", "commit", "-m", "P2.6 supervisor bridge/control artifacts"], cwd=BRIDGE_DIR)
    remotes = run(["git", "remote"], cwd=BRIDGE_DIR, check=False).stdout.split()
    if REMOTE_NAME not in remotes:
        if DEFAULT_REMOTE:
            run(["git", "remote", "add", REMOTE_NAME, DEFAULT_REMOTE], cwd=BRIDGE_DIR)
        else:
            print("GITHUB_HUMAN_ACTION_REQUIRED")
            print("No git remote configured for the bridge repo.")
            print("Minimal action: create GitHub repo eve-agent-lab (or set EVE_AGENT_LAB_REMOTE)")
            print("then: git -C", BRIDGE_DIR, "remote add origin <url> && rerun publish")
            return 3
    push = subprocess.run(
        ["git", "push", "-u", REMOTE_NAME, "HEAD"],
        cwd=BRIDGE_DIR,
        text=True,
        capture_output=True,
    )
    if push.returncode != 0:
        print("PUSH_FAILED")
        print(_redact((push.stderr or push.stdout or "").strip()))
        print("GITHUB_HUMAN_ACTION_REQUIRED")
        return push.returncode or 4
    print("PUSH_OK")
    print(_redact((push.stdout or "").strip()))
    return 0


def cmd_pull() -> int:
    if not (BRIDGE_DIR / ".git").exists():
        raise SyncError("bridge git repo not initialized; run publish after remote exists", 3)
    remotes = run(["git", "remote"], cwd=BRIDGE_DIR, check=False).stdout.split()
    if REMOTE_NAME not in remotes:
        raise SyncError("no origin remote; GITHUB_HUMAN_ACTION_REQUIRED", 3)
    pull = subprocess.run(
        ["git", "pull", "--ff-only", REMOTE_NAME],
        cwd=BRIDGE_DIR,
        text=True,
        capture_output=True,
    )
    if pull.returncode != 0:
        print("PULL_FAILED")
        print(_redact((pull.stderr or pull.stdout or "").strip()))
        return pull.returncode or 4
    print("PULL_OK")
    print(_redact((pull.stdout or "").strip()))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Supervisor bridge sync (explicit, single-shot)")
    parser.add_argument("command", choices=["status", "publish", "pull"])
    args = parser.parse_args()
    try:
        if args.command == "status":
            return cmd_status()
        if args.command == "publish":
            return cmd_publish()
        return cmd_pull()
    except SyncError as exc:
        print("ERROR", _redact(str(exc)))
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
