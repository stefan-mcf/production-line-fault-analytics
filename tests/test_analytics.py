import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analytics import build_report, load_exports
from scripts.generate_fixture import generate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BATCHES = sorted(DATA.glob("*.csv"))
REVIEW = DATA / "practice-review.json"


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.report = build_report(BATCHES, REVIEW)
        self.investigation = self.report["investigation"]

    def test_row_reconciliation_and_replay_origins(self):
        self.assertEqual(self.report["ingestion"], {
            "input_rows": 23,
            "accepted_events": 16,
            "duplicate_rows": 3,
            "invalid_rows": 2,
            "conflict_rows": 2,
        })
        events = {record["event_id"]: record for record in self.report["events"]}
        self.assertNotIn("PROFILE-588", events)
        self.assertEqual(events["ABORT-610"]["origins"], [
            {"batch": "events-01.csv", "row": 4},
            {"batch": "events-02.csv", "row": 2},
        ])
        for event in events.values():
            for source in event["origins"]:
                with (DATA / source["batch"]).open(newline="", encoding="utf-8") as handle:
                    raw = list(csv.reader(handle))[source["row"] - 1]
                self.assertEqual(raw, [
                    event["event_id"], event["station"], event["code"],
                    event["started_at"], event["cleared_at"] or "",
                ])

    def test_open_and_overnight_intervals(self):
        targets = {episode["event"]["event_id"]: episode["event"] for episode in self.investigation["episodes"]}
        self.assertEqual(len(targets), 5)
        self.assertEqual(targets["ABORT-639"]["duration_seconds"], 157)
        self.assertIsNone(targets["ABORT-652"]["cleared_at"])
        self.assertIsNone(targets["ABORT-652"]["duration_seconds"])

    def test_same_episode_support_and_tied_time(self):
        episodes = {item["event"]["event_id"]: item for item in self.investigation["episodes"]}
        self.assertEqual([item["event_id"] for item in episodes["ABORT-624"]["preceding"]],
                         ["CONTACT-437", "PROFILE-571", "CONTACT-442"])
        self.assertEqual([item["event_id"] for item in episodes["ABORT-639"]["preceding"]], ["RETRY-826"])
        self.assertEqual([item["lead_seconds"] for item in episodes["ABORT-652"]["preceding"]], [240, 127])
        self.assertEqual([item["event_id"] for item in episodes["ABORT-667"]["preceding"]], ["CONTACT-479"])
        singles = {item["code"]: item["support"] for item in self.investigation["candidates"]}
        self.assertEqual(singles, {"CONTACT_CHECK": 4, "PROFILE_RELOAD": 2, "SESSION_RETRY": 2})
        pairs = {frozenset(condition["code"] for condition in item["conditions"]): item["support"]
                 for item in self.investigation["pair_candidates"]}
        self.assertEqual(pairs, {
            frozenset(("CONTACT_CHECK", "PROFILE_RELOAD")): 2,
            frozenset(("CONTACT_CHECK", "SESSION_RETRY")): 1,
        })

    def test_review_is_preserved_as_practice(self):
        self.assertEqual(self.report["review"], json.loads(REVIEW.read_text(encoding="utf-8")))
        self.assertEqual(self.report["review"]["state"], "practice")
        self.assertEqual(self.report["review"]["assessment"], "insufficient_evidence")

    def test_duplicate_batch_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "filenames must be distinct"):
            load_exports([BATCHES[0], BATCHES[0]])

    def test_origin_counts_blank_lines_in_the_export(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "events.csv"
            header, first_event = BATCHES[0].read_text(encoding="utf-8").splitlines()[:2]
            source.write_text(f"{header}\n\n{first_event}\n", encoding="utf-8")
            accepted, _, _ = load_exports([source])
            self.assertEqual(list(accepted.values()), [[{"batch": "events.csv", "row": 3}]])

    def test_fixture_and_report_reproduce_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            generated = Path(temp) / "data"
            output = Path(temp) / "report"
            generate(generated)
            for source in (*BATCHES, REVIEW):
                self.assertEqual((generated / source.name).read_bytes(), source.read_bytes())
            subprocess.run([
                sys.executable, str(ROOT / "analytics.py"),
                *(str(generated / batch.name) for batch in reversed(BATCHES)),
                "--review", str(generated / REVIEW.name), "--out", str(output),
            ], check=True, capture_output=True)
            for name in ("example-report.json", "example-report.md"):
                self.assertEqual((output / name).read_bytes(), (ROOT / "report" / name).read_bytes())

    def test_reconciliation_comparison_reproduces(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "reconciliation-check.json"
            subprocess.run([
                sys.executable, "-B", str(ROOT / "scripts" / "evaluate_reconciliation.py"),
                "--output", str(output),
            ], check=True, capture_output=True)
            self.assertEqual(output.read_bytes(), (ROOT / "report" / output.name).read_bytes())
            comparison = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(comparison["ingestion"], self.report["ingestion"])
        self.assertEqual(comparison["target_counts"], {
            "raw_matching_rows": 7, "valid_matching_rows": 6, "reconciled_episodes": 5,
        })
        reload = comparison["profile_reload"]
        self.assertEqual(reload["as_reconciled"], {
            "support": 2, "total_episodes": 5, "episode_ids": ["ABORT-624", "ABORT-652"],
        })
        self.assertEqual([case["origin"] for case in reload["if_admitted"]], [
            {"batch": "events-01.csv", "row": 12}, {"batch": "events-02.csv", "row": 11},
        ])
        self.assertEqual([case["cleared_at"] for case in reload["if_admitted"]], [
            "2042-10-16T09:41:04Z", "2042-10-16T09:40:53Z",
        ])
        for case in reload["if_admitted"]:
            self.assertEqual((case["support"], case["total_episodes"]), (3, 5))
            self.assertEqual(case["episode_ids"], ["ABORT-624", "ABORT-652", "ABORT-667"])


if __name__ == "__main__":
    unittest.main()
