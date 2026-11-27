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


class PlanTests(unittest.TestCase):
    def test_codex_spends_soonest_available_credit_inside_window(self) -> None:
        account = {
            "provider": "openai-codex",
            "credentialId": 1,
            "credits": [
                {"id": "later", "status": "available", "expiresAt": stamp(timedelta(days=11))},
                {"id": "redeemed", "status": "redeemed", "expiresAt": stamp(timedelta(hours=1))},
                {"id": "expiring", "status": "available", "expiresAt": stamp(timedelta(hours=11))},
                {"id": "lapsed", "status": "available", "expiresAt": stamp(-timedelta(minutes=1))},
            ],
        }

        spends, stranded = GUARD["plan"]([account], NOW, DEADLINE)

        self.assertEqual([(spend.target, spend.credit_id) for spend in spends], [("openai-codex/1", "expiring")])
        self.assertEqual(stranded, [])

    def test_codex_holds_credits_outside_window(self) -> None:
        account = {
            "provider": "openai-codex",
            "credentialId": 1,
            "credits": [{"id": "later", "status": "available", "expiresAt": stamp(timedelta(hours=13))}],
        }

        self.assertEqual(GUARD["plan"]([account], NOW, DEADLINE), ([], []))

    def test_claude_spends_only_the_selected_usable_credit(self) -> None:
        account = {
            "provider": "anthropic",
            "credentialId": 7,
            "nextCreditId": "selected",
            "credits": [
                {"id": "selected", "status": "available", "usable": True, "expiresAt": stamp(timedelta(hours=2))},
                {"id": "other", "status": "available", "usable": False, "expiresAt": stamp(timedelta(hours=3))},
                {"id": "locked", "status": "unavailable", "usable": False, "expiresAt": stamp(timedelta(hours=1))},
            ],
        }

        spends, stranded = GUARD["plan"]([account], NOW, DEADLINE)

        self.assertEqual([(spend.target, spend.credit_id) for spend in spends], [("anthropic/7", "selected")])
        self.assertEqual([credit.credit_id for credit in stranded], ["other"])

    def test_claude_reports_expiring_credit_the_provider_did_not_select(self) -> None:
        account = {
            "provider": "anthropic",
            "credentialId": 7,
            "nextCreditId": "fable",
            "credits": [
                {"id": "fable", "status": "available", "usable": True, "expiresAt": stamp(timedelta(days=90))},
                {"id": "monthly", "status": "available", "usable": False, "expiresAt": stamp(timedelta(hours=4))},
            ],
        }

        spends, stranded = GUARD["plan"]([account], NOW, DEADLINE)

        self.assertEqual(spends, [])
        self.assertEqual([credit.credit_id for credit in stranded], ["monthly"])


if __name__ == "__main__":
    unittest.main()
