"""Reconcile equipment-event exports and build a source-linked investigation."""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path


FIELDS = ("event_id", "station", "code", "start_utc", "clear_utc")
STATIONS = frozenset(("test_bench", "programmer", "fixture_station"))
TARGET = {"station": "test_bench", "code": "CYCLE_ABORT"}
LOOKBACK_SECONDS = 240


@dataclass(frozen=True)
class Event:
    event_id: str
    station: str
    code: str
    start: datetime
    clear: datetime | None

    @property
    def condition(self) -> tuple[str, str]:
        return self.station, self.code


def timestamp(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("expected UTC timestamp with second precision")
    return datetime.fromisoformat(value)


def parse_event(row: dict) -> Event:
    if None in row or any(value is None for value in row.values()):
        raise ValueError("wrong number of fields")
    if not re.fullmatch(r"[A-Z]+-[0-9]+", row["event_id"]):
        raise ValueError("invalid event ID")
    if row["station"] not in STATIONS:
        raise ValueError("unknown station")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,31}", row["code"]):
        raise ValueError("invalid fault code")
    start = timestamp(row["start_utc"])
    clear = timestamp(row["clear_utc"]) if row["clear_utc"] else None
    if clear is not None and clear < start:
        raise ValueError("clear precedes start")
    return Event(row["event_id"], row["station"], row["code"], start, clear)


def load_exports(inputs: list[Path]) -> tuple[dict, dict, list]:
    if len({path.name for path in inputs}) != len(inputs):
        raise ValueError("input batch filenames must be distinct")
    grouped = defaultdict(list)
    rejected = []
    counts = dict(input_rows=0, accepted_events=0, duplicate_rows=0, invalid_rows=0, conflict_rows=0)
    for path in sorted(inputs, key=lambda item: item.name):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError(f"unexpected export header in {path.name}")
            for row in reader:
                origin = {"batch": path.name, "row": reader.line_num}
                counts["input_rows"] += 1
                try:
                    event = parse_event(row)
                except ValueError as error:
                    rejected.append({"kind": "invalid", "reason": str(error), "origin": origin})
                    counts["invalid_rows"] += 1
                    continue
                grouped[event.event_id].append((event, origin))
    accepted = {}
    for event_id, versions in sorted(grouped.items()):
        event = versions[0][0]
        if any(candidate != event for candidate, _ in versions):
            for _, origin in versions:
                rejected.append({"kind": "conflict", "reason": f"conflicting rows for {event_id}", "origin": origin})
            counts["conflict_rows"] += len(versions)
            continue
        accepted[event] = [origin for _, origin in versions]
        counts["duplicate_rows"] += len(versions) - 1
    counts["accepted_events"] = len(accepted)
    return accepted, counts, rejected


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def event_record(event: Event, origins: list[dict]) -> dict:
    return {
        "event_id": event.event_id,
        "station": event.station,
        "code": event.code,
        "started_at": iso(event.start),
        "cleared_at": iso(event.clear) if event.clear is not None else None,
        "duration_seconds": int((event.clear - event.start).total_seconds()) if event.clear is not None else None,
        "origins": origins,
    }


def condition_record(condition: tuple[str, str]) -> dict:
    return {"station": condition[0], "code": condition[1]}


def investigate(accepted: dict) -> dict:
    ordered = sorted(accepted, key=lambda event: (event.start, event.event_id))
    target_condition = TARGET["station"], TARGET["code"]
    targets = [event for event in ordered if event.condition == target_condition]
    episodes = []
    singles = Counter()
    pairs = Counter()
    for target in targets:
        preceding = []
        conditions = set()
        for event in ordered:
            lead = int((target.start - event.start).total_seconds())
            if event.station != target.station and 0 < lead <= LOOKBACK_SECONDS:
                preceding.append({**event_record(event, accepted[event]), "lead_seconds": lead})
                conditions.add(event.condition)
        singles.update(conditions)
        pairs.update(combinations(sorted(conditions), 2))
        episodes.append({"event": event_record(target, accepted[target]), "preceding": preceding})
    total = len(episodes)
    return {
        "target": TARGET,
        "lookback_seconds": LOOKBACK_SECONDS,
        "episodes": episodes,
        "candidates": [
            {**condition_record(condition), "support": support, "total_episodes": total}
            for condition, support in sorted(singles.items(), key=lambda item: (-item[1], item[0]))
        ],
        "pair_candidates": [
            {"conditions": [condition_record(item) for item in pair], "support": support, "total_episodes": total}
            for pair, support in sorted(pairs.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def build_report(inputs: list[Path], practice_review: Path) -> dict:
    accepted, counts, rejected = load_exports(inputs)
    review = json.loads(practice_review.read_text(encoding="utf-8"))
    if (
        not isinstance(review, dict)
        or set(review) != {"state", "target", "assessment", "next_check"}
        or review.get("state") != "practice"
        or review.get("target") != TARGET
        or review.get("assessment") != "insufficient_evidence"
        or not isinstance(review.get("next_check"), str)
        or not review["next_check"].strip()
    ):
        raise ValueError("expected a practice review with an insufficient-evidence assessment and a next check")
    return {
        "schema_version": 1,
        "ingestion": counts,
        "events": [event_record(event, origins) for event, origins in accepted.items()],
        "quarantine": rejected,
        "investigation": investigate(accepted),
        "review": review,
    }


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def origin_labels(origins: list[dict]) -> str:
    return ", ".join(f"{cell(origin['batch'])} row {origin['row']}" for origin in origins)


def render_markdown(report: dict) -> str:
    counts = report["ingestion"]
    investigation = report["investigation"]
    lines = [
        "# Example investigation — synthetic data",
        "",
        f"{counts['input_rows']} export rows reconciled to {counts['accepted_events']} unique accepted events. "
        f"{counts['duplicate_rows']} replay rows retain source references. "
        f"Quarantine contains {counts['conflict_rows']} conflicting and {counts['invalid_rows']} invalid rows.",
        "",
        "## Qualification-cycle aborts",
        "",
        f"Starts within the preceding {investigation['lookback_seconds']} seconds count once per condition per episode. "
        "Paired conditions must occur in the same lookback. Tied starts are excluded.",
        "",
        "| Other-station condition | Episodes supported |",
        "| --- | ---: |",
    ]
    for candidate in investigation["candidates"]:
        lines.append(f"| {candidate['station']} / `{candidate['code']}` | {candidate['support']} / {candidate['total_episodes']} |")
    lines.extend(("", "| Same-episode pair | Episodes supported |", "| --- | ---: |"))
    for pair in investigation["pair_candidates"]:
        label = " + ".join(f"{item['station']} / `{item['code']}`" for item in pair["conditions"])
        lines.append(f"| {label} | {pair['support']} / {pair['total_episodes']} |")
    lines.extend(("", "## Source-linked episodes", ""))
    for episode in investigation["episodes"]:
        event = episode["event"]
        duration = event["duration_seconds"]
        duration_text = f"{duration} s recorded interval" if duration is not None else "clear time unknown"
        lines.extend((
            f"- **{event['event_id']}** at {event['started_at']} ({duration_text}). {origin_labels(event['origins'])}.",
            *(
                f"  - {prior['event_id']} · {prior['station']} / `{prior['code']}`, "
                f"{prior['lead_seconds']} s earlier. {origin_labels(prior['origins'])}."
                for prior in episode["preceding"]
            ),
        ))
    lines.extend((
        "", "## Practice review", "",
        "The assessment was **insufficient evidence**.", "",
        report["review"]["next_check"], "",
        "The timing evidence supports a follow-up check. Establishing a cause or prediction performance requires separate evidence.",
        "",
    ))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.inputs, args.review)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"Could not build investigation: {error}\n")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "example-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.out / "example-report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote example-report.json and example-report.md to {args.out}")


if __name__ == "__main__":
    main()
