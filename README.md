# Production Line Fault Analytics

Five qualification cycles aborted on a fictional electronics test bench. A fixture contact check appeared in the four minutes before **four of the five aborts**. The practice review records insufficient evidence and calls for a reference run to compare the programmer session log with the bench abort record.

[Case study](docs/case-study.md) · [Example report](report/example-report.md) · [Run locally](#run-locally)

![Timeline of five synthetic test-bench aborts and the conditions that preceded them](assets/fault-investigation.png)

## Log imports and fault review

The two CSV exports record some events twice. The Python analyser counts exact repeats once and retains each source row. When two rows for the same event disagree, it quarantines both and records the conflict.

The analyser counts how many aborts each earlier condition preceded. Two contact checks before the same abort add one to that condition’s count. The [case study](docs/case-study.md) follows the individual events and explains how these rules affect the result.

## Run locally

Requires Python 3.11+ and Make. The demo uses the bundled synthetic CSVs and runs offline.

```sh
make demo
make check
```

The demo writes a Markdown brief and JSON report to `outputs/demo/`. The tests verify source references, timing boundaries and exact reproduction of both [checked-in reports](report/).
