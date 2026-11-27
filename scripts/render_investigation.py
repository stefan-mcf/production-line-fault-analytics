"""Render a PNG from the synthetic investigation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import fill
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
INK = "#14243a"
MUTED = "#4c5d70"
LIGHT = "#e5ebf1"
PANEL = "#f6f8fb"
COLORS = ("#066b62", "#4e56a0", "#a45322")


def condition_key(condition: dict[str, Any]) -> tuple[str, str]:
    return condition["station"], condition["code"]


def condition_label(condition: dict[str, Any]) -> str:
    station, code = condition_key(condition)
    return f"{station.replace('_', ' ').capitalize()} · {code.replace('_', ' ').lower()}"


def render(report: dict[str, Any], output: Path) -> None:
    investigation = report["investigation"]
    episodes = investigation["episodes"]
    candidates = investigation["candidates"][:3]
    pairs = investigation["pair_candidates"]
    window_minutes = investigation["lookback_seconds"] / 60
    palette = dict(zip(map(condition_key, candidates), COLORS))

    figure = Figure(figsize=(8.5, 4.55), dpi=160, facecolor="white")
    FigureCanvasAgg(figure)
    figure.text(0.075, 0.923, "FICTIONAL ELECTRONICS QUALIFICATION CELL", color=COLORS[0], weight="bold", size=9)
    figure.text(0.075, 0.838, "What preceded each test abort?", color=INK, weight="bold", size=24)
    figure.text(
        0.075, 0.780,
        f"{len(episodes)} synthetic cycles aligned at the abort. Dots show earlier event starts.",
        color=MUTED, size=9.6,
    )

    figure.text(0.075, 0.697, "Event sequence", color=INK, weight="bold", size=11)
    timeline = figure.add_axes((0.101, 0.240, 0.453, 0.410), facecolor=PANEL)
    timeline.set_axisbelow(True)
    timeline.grid(color=LIGHT, linewidth=0.7)
    timeline.axvline(0, color=INK, linewidth=0.9, alpha=0.55)
    for number, episode in enumerate(episodes, start=1):
        markers = episode["preceding"]
        timeline.scatter(
            [-event["lead_seconds"] / 60 for event in markers],
            [number] * len(markers),
            c=[palette.get(condition_key(event), "#8191a1") for event in markers],
            edgecolors="white", linewidths=0.45, s=29, zorder=3,
        )
    timeline.scatter([0] * len(episodes), range(1, len(episodes) + 1), marker="D", s=23, color=INK)
    timeline.set_xlim(-window_minutes * 1.025, window_minutes * 0.045)
    timeline.set_ylim(len(episodes) + 0.55, 0.45)
    label_interval = (len(episodes) + 11) // 12 or 1
    tick_rows = range(1, len(episodes) + 1, label_interval)
    timeline.set_yticks(tick_rows, [episodes[row - 1]["event"]["event_id"] for row in tick_rows])
    timeline.set_xticks([-window_minutes * step / 4 for step in range(4, -1, -1)])
    timeline.xaxis.set_major_formatter(FuncFormatter(lambda minute, _: f"{abs(minute):g}"))
    timeline.tick_params(length=0, pad=5, labelsize=8, colors=MUTED)
    timeline.set_xlabel("Minutes before the recorded abort", labelpad=7, fontsize=9, color=MUTED)
    for spine in timeline.spines.values():
        spine.set_visible(False)

    figure.text(0.075, 0.125, "◆  Recorded cycle abort", color=INK, size=8.5)
    if len(investigation["candidates"]) > len(candidates):
        figure.text(0.265, 0.125, "●  Other preceding event", color=MUTED, size=8.5)

    figure.text(0.620, 0.697, "Preceding conditions", color=INK, weight="bold", size=11)
    figure.text(0.620, 0.656, "Distinct aborts with each condition", color=MUTED, size=8.5)
    support_plot = figure.add_axes((0.620, 0.235, 0.315, 0.387))
    support_plot.set(xlim=(0, 1), ylim=(0, 1))
    support_plot.set_axis_off()
    for index, (candidate, color) in enumerate(zip(candidates, COLORS)):
        y = 0.88 - index * 0.24
        rate = candidate["support"] / candidate["total_episodes"]
        support_plot.text(0, y, condition_label(candidate), color=INK, fontsize=8.5, va="center")
        support_plot.text(
            1, y, f"{candidate['support']} / {candidate['total_episodes']}",
            color=INK, fontsize=8.5, ha="right", va="center", weight="bold",
        )
        support_plot.barh(y - 0.10, 1, height=0.032, color=LIGHT)
        support_plot.barh(y - 0.10, rate, height=0.032, color=color)
    if not candidates:
        support_plot.text(0, 0.88, "No preceding conditions in the window", color=MUTED, fontsize=9)
    if pairs:
        pair = pairs[0]
        stations = " + ".join(condition_label(condition) for condition in pair["conditions"])
        pair_label = f"{fill(stations, width=49)}\n{pair['support']} / {pair['total_episodes']} episodes"
        figure.text(0.620, 0.211, "Example pair", color=INK, size=8.8, weight="bold")
        figure.text(0.620, 0.181, pair_label, color=MUTED, size=8.1, va="top")

    figure.text(
        0.075, 0.056,
        "Timing supports investigation. Establishing a cause requires independent evidence.",
        color=MUTED, size=8.5,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=figure.dpi, metadata={"Title": "Fictional electronics qualification event timing"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "report" / "example-report.json")
    parser.add_argument("--output", type=Path, default=ROOT / "assets" / "fault-investigation.png")
    args = parser.parse_args()
    render(json.loads(args.report.read_text(encoding="utf-8")), args.output)


if __name__ == "__main__":
    main()
