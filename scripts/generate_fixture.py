"""Generate the invented event exports and review bundled with this example."""

import argparse
import csv
import json
from pathlib import Path


HEADER = ("event_id", "station", "code", "start_utc", "clear_utc")
FIRST = (
    ("CONTACT-431", "fixture_station", "CONTACT_CHECK", "2042-10-14T16:34:07Z", "2042-10-14T16:34:25Z"),
    ("RETRY-817", "programmer", "SESSION_RETRY", "2042-10-14T16:36:15Z", "2042-10-14T16:36:32Z"),
    ("ABORT-610", "test_bench", "CYCLE_ABORT", "2042-10-14T16:37:19Z", "2042-10-14T16:37:49Z"),
    ("CONTACT-437", "fixture_station", "CONTACT_CHECK", "2042-10-14T17:07:44Z", "2042-10-14T17:08:04Z"),
    ("PROFILE-571", "programmer", "PROFILE_RELOAD", "2042-10-14T17:09:57Z", "2042-10-14T17:10:26Z"),
    ("CONTACT-442", "fixture_station", "CONTACT_CHECK", "2042-10-14T17:11:04Z", "2042-10-14T17:11:10Z"),
    ("ABORT-624", "test_bench", "CYCLE_ABORT", "2042-10-14T17:11:42Z", "2042-10-14T17:12:24Z"),
    ("RETRY-826", "programmer", "SESSION_RETRY", "2042-10-15T23:58:09Z", "2042-10-15T23:58:24Z"),
    ("ABORT-639", "test_bench", "CYCLE_ABORT", "2042-10-15T23:59:37Z", "2042-10-16T00:02:14Z"),
    ("CONTACT-457", "fixture_station", "CONTACT_CHECK", "2042-10-15T23:59:37Z", "2042-10-15T23:59:55Z"),
    ("PROFILE-588", "programmer", "PROFILE_RELOAD", "2042-10-16T09:40:29Z", "2042-10-16T09:41:04Z"),
    ("ABORT-659", "test_bench", "CYCLE_ABORT", "2042-10-16T08:17:44Z", "2042-10-16T08:17:39Z"),
)
SECOND = (
    FIRST[2],
    FIRST[3],
    FIRST[7],
    ("CONTACT-463", "fixture_station", "CONTACT_CHECK", "2042-10-16T06:59:51Z", "2042-10-16T07:00:05Z"),
    ("PROFILE-593", "programmer", "PROFILE_RELOAD", "2042-10-16T07:01:44Z", "2042-10-16T07:02:19Z"),
    ("ABORT-652", "test_bench", "CYCLE_ABORT", "2042-10-16T07:03:51Z", ""),
    ("RETRY-844", "programmer", "SESSION_RETRY", "2042-10-16T09:38:07Z", "2042-10-16T09:38:23Z"),
    ("CONTACT-479", "fixture_station", "CONTACT_CHECK", "2042-10-16T09:41:36Z", "2042-10-16T09:41:43Z"),
    ("ABORT-667", "test_bench", "CYCLE_ABORT", "2042-10-16T09:42:08Z", "2042-10-16T09:42:20Z"),
    ("PROFILE-588", "programmer", "PROFILE_RELOAD", "2042-10-16T09:40:29Z", "2042-10-16T09:40:53Z"),
    ("CHECK-491", "unregistered_station", "CONTACT_CHECK", "2042-10-16T09:40:56Z", "2042-10-16T09:41:12Z"),
)
REVIEW = {
    "state": "practice",
    "target": {"station": "test_bench", "code": "CYCLE_ABORT"},
    "assessment": "insufficient_evidence",
    "next_check": "Run a reference module through the qualification cycle and compare the programmer session log with the bench abort record.",
}


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for index, rows in enumerate((FIRST, SECOND), start=1):
        with (output / f"events-{index:02d}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(HEADER)
            writer.writerows(rows)
    (output / "practice-review.json").write_text(json.dumps(REVIEW, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("data"))
    generate(parser.parse_args().output)
