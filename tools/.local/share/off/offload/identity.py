import hashlib
import json
import os
import re
import socket
import subprocess
from pathlib import Path, PurePosixPath

from .config import OffloadConfig

BASE_SCHEMA = "off-base-v3"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def token(name: str, identity: str, limit: int) -> str:
    """A dashless name part: worker names are split on dashes, and the hash keeps truncated names apart."""
    stem = _NON_ALNUM.sub("", name.lower())[:limit]
    return f"{stem}{hashlib.sha256(identity.encode()).hexdigest()[:4]}"


def host_slug() -> str:
    host = os.environ.get("OFF_HOST") or socket.gethostname()
    return token(host, host, 10)


def repo_slug(root: Path) -> str:
    origin = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if origin.returncode != 0:
        return token(root.name, str(root.resolve()), 16)
    url = origin.stdout.strip().rstrip("/")
    return token(PurePosixPath(url.replace(":", "/")).name.removesuffix(".git"), url, 16)


def worker_name(host: str, repo: str, index: int) -> str:
    return f"off-{host}-{repo}-{index}"


def worker_prefix(host: str, repo: str | None) -> str:
    if repo is None:
        return f"off-{host}-"
    return f"off-{host}-{repo}-"


def base_key(config: OffloadConfig) -> str:
    inputs = {
        path: hashlib.sha256((config.root / path).read_bytes()).hexdigest()
        for path in sorted(config.setup.inputs)
    }
    manifest = json.dumps(
        {
            "schema": BASE_SCHEMA,
            "run": list(config.setup.run),
            "inputs": inputs,
            "setup_egress": list(config.worker.setup_egress),
        },
        sort_keys=True,
    )
    return hashlib.sha256(manifest.encode()).hexdigest()[:12]
