import hashlib
import json
from typing import Final

from .config import WorkerSpec


def setup_network_rules(worker: WorkerSpec) -> list[dict[str, str]]:
    return [{"include": "defaults"}, *_allow(worker.setup_egress + worker.egress)]


def run_network_rules(worker: WorkerSpec) -> list[dict[str, str]]:
    return [{"domain": "*", "action": "deny"}, *_allow(worker.egress)]


LOCKED_PRIVILEGES: Final = {"profile": "standard", "noNewPrivileges": True}


def memory_policy(memory_mb: int) -> dict[str, object]:
    return {"memory": {"limit_mb": memory_mb, "autoscale": False}}


def policy_hash(worker: WorkerSpec) -> str:
    payload = json.dumps(
        {
            "network": run_network_rules(worker),
            "memory": memory_policy(worker.memory_mb),
            "privileges": LOCKED_PRIVILEGES,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def _allow(domains: tuple[str, ...]) -> list[dict[str, str]]:
    return [{"domain": domain, "action": "allow"} for domain in domains]
