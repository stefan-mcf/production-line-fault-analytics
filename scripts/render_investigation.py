"""Render a PNG from the synthetic investigation report."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from textwrap import shorten
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
INK = "#152839"
MUTED = "#4b5d68"
GRID = "#dee5ea"
CONDITION_STYLES = (("o", "#00796d"), ("s", "#466377"), ("^", "#a56224"))
OTHER_STYLE = ("x", "#6d7c86")
ABORT_STYLE = ("D", INK)


def condition_key(condition: dict[str, Any]) -> tuple[str, str]:
    return condition["station"], condition["code"]


def condition_label(condition: dict[str, Any]) -> str:
    return condition["code"].replace("_", " ").capitalize()


def legend_marker(label: str, style: tuple[str, str]) -> Line2D:
    marker, color = style
    return Line2D([], [], linestyle="none", marker=marker, color=color, markersize=6.2, label=label)


def figure_title(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "Events preceding recorded aborts"
    leading = candidates[0]
    count = f"{leading['support']} of {leading['total_episodes']} aborts"
    if condition_key(leading) == ("fixture_station", "CONTACT_CHECK"):
        return f"Contact checks preceded {count}"
    return f"{shorten(condition_label(leading), width=30)} before {count}"


def render(report: dict[str, Any], output: Path) -> None:
    investigation = report["investigation"]
    episodes = investigation["episodes"]
    candidates = investigation["candidates"][:3]
    window_minutes = investigation["lookback_seconds"] / 60
    styles = dict(zip(map(condition_key, candidates), CONDITION_STYLES))
    labels = [condition_label(candidate) for candidate in candidates]
    title = figure_title(candidates)
    points = defaultdict(list)
    for row, episode in enumerate(episodes, start=1):
        for event in episode["preceding"]:
            style = styles.get(condition_key(event), OTHER_STYLE)
            points[style].append((-event["lead_seconds"] / 60, row))
    other_starts = OTHER_STYLE in points

    figure = Figure(figsize=(8.5, 3.7), dpi=216, facecolor="white")
    FigureCanvasAgg(figure)
    figure.text(0.045, 0.915, title, color=INK, weight="bold", size=18, va="center")

    handles = []
    for candidate, label in zip(candidates, labels):
        if labels.count(label) > 1:
            label = f"{candidate['station'].replace('_', ' ').capitalize()} · {label.lower()}"
        label = shorten(label, width=30, placeholder="…")
        count = f"{candidate['support']}/{candidate['total_episodes']}"
        handles.append(legend_marker(f"{label}  {count}", styles[condition_key(candidate)]))
    if other_starts:
        handles.append(legend_marker("Other starts", OTHER_STYLE))
    handles.append(legend_marker("Recorded abort", ABORT_STYLE))
    legend_columns = 3 if other_starts or sum(len(handle.get_label()) for handle in handles) > 85 else len(handles)
    figure.legend(
        handles=handles, loc="upper left", bbox_to_anchor=(0.043, 0.85), ncols=legend_columns,
        fontsize=10.5, labelcolor=INK, frameon=False, borderaxespad=0, handletextpad=0.4,
        columnspacing=1.3, handlelength=1.2,
    )

    plot_top = 0.695 if legend_columns < len(handles) else 0.75
    timeline = figure.add_axes((0.165, 0.24, 0.79, plot_top - 0.24))
    timeline.set_axisbelow(True)
    timeline.grid(color=GRID, linewidth=0.8)
    timeline.axvline(0, color=INK, linewidth=1, alpha=0.65)
    for (marker, color), positions in points.items():
        times, rows = zip(*positions)
        timeline.scatter(times, rows, marker=marker, color=color, s=42, zorder=3)
    abort_marker, abort_color = ABORT_STYLE
    timeline.scatter(
        [0] * len(episodes), range(1, len(episodes) + 1),
        marker=abort_marker, s=38, color=abort_color, zorder=4,
    )
    timeline.set_xlim(-window_minutes * 1.05, window_minutes * 0.05)
    timeline.set_ylim(len(episodes) + 0.58, 0.42)
    label_interval = (len(episodes) + 11) // 12 or 1
    tick_rows = range(1, len(episodes) + 1, label_interval)
    timeline.set_yticks(tick_rows, [episodes[row - 1]["event"]["event_id"] for row in tick_rows])
    timeline.set_xticks([-window_minutes * step / 4 for step in range(4, -1, -1)])
    timeline.xaxis.set_major_formatter(FuncFormatter(lambda minute, _: f"−{abs(minute):g}" if minute < 0 else "0"))
    timeline.tick_params(length=0, pad=6, labelsize=10.5, colors=MUTED)
    for label in timeline.get_yticklabels():
        label.set_fontfamily("DejaVu Sans Mono")
    timeline.text(0, 1.025, "Abort", transform=timeline.get_xaxis_transform(), ha="center", color=INK, size=10)
    timeline.set_xlabel("Minutes relative to recorded abort", labelpad=7, fontsize=10.5, color=MUTED)
    for spine in timeline.spines.values():
        spine.set_visible(False)

    if candidates:
        figure.text(0.045, 0.065, "Fractions count distinct aborts.", color=MUTED, size=9.2)
    figure.text(0.955, 0.065, "Generated test data", color=MUTED, size=9.2, ha="right")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=figure.dpi, metadata={"Title": title})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "report" / "example-report.json")
    parser.add_argument("--output", type=Path, default=ROOT / "assets" / "fault-investigation.png")
    args = parser.parse_args()
    render(json.loads(args.report.read_text(encoding="utf-8")), args.output)


if __name__ == "__main__":
    main()
