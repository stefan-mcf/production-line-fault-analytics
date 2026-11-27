# Production Line Fault Analytics

Production Line Fault Analytics reconciles overlapping CSV exports and traces recurring equipment stops to their supporting records. The offline Python analyser counts earlier conditions across distinct episodes and produces a Markdown investigation brief and structured JSON evidence.

The worked example uses a fictional electronics qualification cell. Reconciling **23 input rows** yields **16 distinct accepted events**, retains **3 exact repeat rows** as additional source origins, and quarantines **2 invalid** and **2 conflicting** rows. Within the four-minute review window, a fixture contact check precedes **4 of 5** test-bench cycle aborts.

[Engineering case study](docs/case-study.md) · [Example investigation](report/example-report.md) · [Scope and deliverables](#scope-and-deliverables) · [Run the demo](#run-the-demo)

## Worked example

![Five fictional test-bench cycle aborts aligned by time, with preceding events and condition counts](assets/fault-investigation.png)

*Aligned timing for five synthetic `CYCLE_ABORT` episodes on `test_bench`, showing preceding other-station events within 240 seconds and episode-level support counts.*

| Investigation summary | Result | Basis |
| :--- | ---: | :--- |
| Input rows reconciled | **23** | Two overlapping synthetic exports ([events-01.csv](data/events-01.csv), [events-02.csv](data/events-02.csv)) |
| Distinct accepted events | **16** | Exact repeats retained as 3 additional source origins |
| Quarantined rows | **4** | 2 invalid rows and 2 conflicting rows for `PROFILE-588` |
| Target stop episodes | **5** | `CYCLE_ABORT` events on `test_bench` |
| Leading preceding condition | **4 / 5** | `fixture_station` / `CONTACT_CHECK` within 240 seconds |
| Practice review outcome | **Insufficient evidence** | Supplied review note in [practice-review.json](data/practice-review.json) |

The example brief records **insufficient evidence** and proposes running a reference module through the qualification cycle, then comparing the programmer session log with the bench abort record. Inspect the full [example investigation](report/example-report.md) and [structured JSON evidence](report/example-report.json).

## Log imports and fault review

Repeated exports from equipment logs can inflate event counts, and conflicting edits can alter the apparent duration or sequence of a stop. The analyser enforces three rules before comparing timings.

| Rule | Implemented behaviour |
| :--- | :--- |
| **Validate and preserve origins** | Check required CSV fields, recognised stations, valid identifiers and codes, and explicit UTC timestamps at second precision. Keep every source batch and row pointer for exact repeats. |
| **Quarantine conflicts** | Compare all valid rows sharing an event identifier and hold every competing version when payloads differ, keeping results independent of import order. |
| **Count episode-level support** | Count each preceding other-station condition at most once per target episode during the 240 seconds before the target start. Tied starts supply no ordering evidence. |

## Scope and deliverables

The runnable deliverable includes the Python analyser, synthetic fixtures and reports, the chart script, and the test suite. The case study documents proposed reporting tables and machine learning evaluations.

| Area | Current state | Primary files |
| :--- | :--- | :--- |
| **CSV reconciliation and investigation** | Implemented and verified offline | [analytics.py](analytics.py) · [report/example-report.md](report/example-report.md) · [report/example-report.json](report/example-report.json) |
| **Synthetic fixture and chart** | Implemented for the fictional qualification cell | [generate_fixture.py](scripts/generate_fixture.py) · [render_investigation.py](scripts/render_investigation.py) · [fault-investigation.png](assets/fault-investigation.png) |
| **Verification suite** | Implemented and runnable via Make | [tests/test_analytics.py](tests/test_analytics.py) · [Makefile](Makefile) |
| **Reporting grain and ML evaluation** | Design plans only | [Engineering case study](docs/case-study.md#reporting-design-plan) |

## Run the demo

Requires Python 3.11+ and Make. The demo runs offline using the bundled CSV files and the Python standard library.

```sh
make demo
make check
```

`make demo` writes the regenerated Markdown brief and JSON evidence package to `outputs/demo/`. `make check` reconciles all input rows, verifies reported source pointers, tests timing and duration edge cases, and confirms byte-for-byte reproduction of both checked-in reports.
