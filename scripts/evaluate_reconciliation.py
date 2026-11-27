"""Measure how reconciliation changes the bundled synthetic investigation."""

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics import TARGET, investigate, load_exports, parse_event


DISPUTED_EVENT_ID = "PROFILE-588"
RELOAD_CONDITION = ("programmer", "PROFILE_RELOAD")


def profile_reload_support(investigation: dict) -> dict:
    episodes = investigation["episodes"]
    episode_ids = [
        episode["event"]["event_id"]
        for episode in episodes
        if any((event["station"], event["code"]) == RELOAD_CONDITION for event in episode["preceding"])
    ]
    return {"support": len(episode_ids), "total_episodes": len(episodes), "episode_ids": episode_ids}


def evaluate_reconciliation(inputs: list[Path]) -> dict:
    accepted, ingestion, quarantine = load_exports(inputs)
    reconciled = investigate(accepted)
    conflicts = {
        (decision["origin"]["batch"], decision["origin"]["row"])
        for decision in quarantine
        if decision["kind"] == "conflict"
    }
    target = TARGET["station"], TARGET["code"]
    raw_count = valid_count = 0
    alternatives = []
    for path in sorted(inputs, key=lambda item: item.name):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            for row in reader:
                if (row["station"], row["code"]) == target:
                    raw_count += 1
                    try:
                        parse_event(row)
                    except ValueError:
                        continue
                    valid_count += 1

                origin = {"batch": path.name, "row": reader.line_num}
                if row["event_id"] == DISPUTED_EVENT_ID and (path.name, reader.line_num) in conflicts:
                    event = parse_event(row)
                    alternative = investigate(accepted | {event: [origin]})
                    alternatives.append({
                        "origin": origin,
                        "cleared_at": row["clear_utc"],
                        **profile_reload_support(alternative),
                    })

    if len(alternatives) != 2:
        raise ValueError(f"expected two quarantined rows for {DISPUTED_EVENT_ID}")

    return {
        "schema_version": 1,
        "fixture": "synthetic",
        "target": TARGET,
        "lookback_seconds": reconciled["lookback_seconds"],
        "ingestion": ingestion,
        "target_counts": {
            "raw_matching_rows": raw_count,
            "valid_matching_rows": valid_count,
            "reconciled_episodes": len(reconciled["episodes"]),
        },
        "profile_reload": {
            "condition": {"station": RELOAD_CONDITION[0], "code": RELOAD_CONDITION[1]},
            "quarantined_event_id": DISPUTED_EVENT_ID,
            "as_reconciled": profile_reload_support(reconciled),
            "if_admitted": alternatives,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = [ROOT / "data" / name for name in ("events-01.csv", "events-02.csv")]
    result = evaluate_reconciliation(inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote reconciliation check to {args.output}")


if __name__ == "__main__":
    main()
