import hashlib
import json
import os
import re
import socket
import subprocess
from pathlib import Path, PurePosixPath

from .config import ConfigError, OffloadConfig

BASE_SCHEMA = "off-base-v1"
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str, limit: int) -> str:
    result = _NON_SLUG.sub("-", text.lower()).strip("-")[:limit].strip("-")
    if not result:
        raise ConfigError(f"cannot build a name from {text!r}")
    return result


def host_slug() -> str:
    return slug(os.environ.get("OFF_HOST") or socket.gethostname(), 12)


def repo_slug(root: Path) -> str:
    origin = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if origin.returncode != 0:
        return slug(root.name, 20)
    url = origin.stdout.strip().rstrip("/").replace(":", "/")
    return slug(PurePosixPath(url).name.removesuffix(".git"), 20)


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
        {"schema": BASE_SCHEMA, "run": list(config.setup.run), "inputs": inputs},
        sort_keys=True,
    )
    return hashlib.sha256(manifest.encode()).hexdigest()[:12]
