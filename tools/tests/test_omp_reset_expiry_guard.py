import runpy
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".local" / "bin" / "omp-reset-expiry-guard"
GUARD = runpy.run_path(str(SCRIPT), run_name="omp_reset_expiry_guard")
NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
DEADLINE = NOW + timedelta(hours=12)


def stamp(delta: timedelta) -> str:
    return (NOW + delta).isoformat().replace("+00:00", "Z")


def cedar(credit_id: str, status: str, usable: bool, expires_in: timedelta, requires_limit: bool = False) -> dict:
    return {
        "id": credit_id,
        "program": "cedar_ember",
        "status": status,
        "remainingCount": 0 if status == "redeemed" else 1,
        "usable": usable,
        "requiresLimit": requires_limit,
        "expiresAt": stamp(expires_in),
    }


def plan(*accounts: dict) -> tuple[list, list]:
    return GUARD["plan"](list(accounts), NOW, DEADLINE)


def spent(spends: list) -> list[tuple[str, str]]:
    return [(spend.target, spend.credit_id) for spend in spends]


def reported(problems: list) -> list[str | None]:
    return [problem.credit_id for problem in problems]


class CodexPlanTests(unittest.TestCase):
    def test_spends_soonest_available_credit_inside_window(self) -> None:
        account = {
            "provider": "openai-codex",
            "credentialId": 1,
            "credits": [
                {"id": "later", "status": "available", "expiresAt": stamp(timedelta(days=11))},
                {"id": "redeemed", "status": "redeemed", "expiresAt": stamp(timedelta(hours=1))},
                {"id": "expiring", "status": "available", "expiresAt": stamp(timedelta(hours=11))},
                {"id": "no-status", "expiresAt": stamp(timedelta(hours=10))},
                {"id": "lapsed", "status": "available", "expiresAt": stamp(-timedelta(minutes=1))},
            ],
        }

        spends, problems = plan(account)

        self.assertEqual(spent(spends), [("openai-codex/1", "no-status")])
        self.assertEqual(problems, [])

    def test_holds_credits_outside_window(self) -> None:
        account = {
            "provider": "openai-codex",
            "credentialId": 1,
            "credits": [{"id": "later", "status": "available", "expiresAt": stamp(timedelta(hours=13))}],
        }

        self.assertEqual(plan(account), ([], []))

    def test_unreadable_expiry_is_reported_without_blocking_other_accounts(self) -> None:
        broken = {
            "provider": "openai-codex",
            "credentialId": 1,
            "credits": [
                {"id": "naive", "status": "available", "expiresAt": "2026-12-01T20:00:00"},
                {"id": "garbage", "status": "available", "expiresAt": "soon"},
            ],
        }
        healthy = {
            "provider": "openai-codex",
            "credentialId": 2,
            "credits": [{"id": "expiring", "status": "available", "expiresAt": stamp(timedelta(hours=3))}],
        }

        spends, problems = plan(broken, healthy)

        self.assertEqual(spent(spends), [("openai-codex/2", "expiring")])
        self.assertEqual(reported(problems), ["naive", "garbage"])


class ClaudePlanTests(unittest.TestCase):
    def test_spends_offered_grant_and_reports_expiring_siblings(self) -> None:
        account = {
            "provider": "anthropic",
            "credentialId": 7,
            "nextCreditId": "selected",
            "credits": [
                cedar("selected", "available", True, timedelta(hours=2)),
                cedar("tenure-locked", "unavailable", False, timedelta(hours=2)),
                cedar("paused", "paused", False, timedelta(hours=5)),
                cedar("used", "redeemed", False, timedelta(hours=1)),
                cedar("later", "unavailable", False, timedelta(days=30)),
            ],
        }

        spends, problems = plan(account)

        self.assertEqual(spent(spends), [("anthropic/7", "selected")])
        self.assertEqual(reported(problems), ["tenure-locked", "paused"])

    def test_reports_selected_grant_on_cooldown_or_needing_a_limit(self) -> None:
        cooldown = {
            "provider": "anthropic",
            "credentialId": 7,
            "nextCreditId": "monthly",
            "credits": [cedar("monthly", "unavailable", False, timedelta(hours=4))],
        }
        needs_limit = {
            "provider": "anthropic",
            "credentialId": 8,
            "nextCreditId": "at-wall",
            "credits": [cedar("at-wall", "available", True, timedelta(hours=4), requires_limit=True)],
        }

        spends, problems = plan(cooldown, needs_limit)

        self.assertEqual(spends, [])
        self.assertEqual(reported(problems), ["monthly", "at-wall"])

    def test_ignores_juniper_session_reset_whose_expiry_is_the_weekly_reset(self) -> None:
        account = {
            "provider": "anthropic",
            "credentialId": 7,
            "nextCreditId": "juniper_tide",
            "credits": [
                {
                    "id": "juniper_tide",
                    "program": "juniper_tide",
                    "status": "available",
                    "remainingCount": 1,
                    "usable": True,
                    "requiresLimit": True,
                    "expiresAt": stamp(timedelta(hours=6)),
                }
            ],
        }

        self.assertEqual(plan(account), ([], []))

    def test_reports_account_whose_listing_failed(self) -> None:
        account = {"provider": "anthropic", "credentialId": 7, "error": "network", "credits": []}

        spends, problems = plan(account)

        self.assertEqual(spends, [])
        self.assertEqual([(problem.account, problem.credit_id) for problem in problems], [("anthropic/7", None)])


if __name__ == "__main__":
    unittest.main()
