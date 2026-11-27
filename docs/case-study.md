# Production Line Fault Analytics case study

An engineer investigating five recurring aborts on a fictional electronics test bench needs to decide where to start. A contact check appears before four of the five stops. To see whether that lead is worth following, the analyser first establishes which records belong to distinct events and which earlier conditions recur across aborts.

[Example report](../report/example-report.md) · [JSON evidence](../report/example-report.json) · [Timing chart](../assets/fault-investigation.png)

## Reconcile the exports

Event `ABORT-610` appears in [the first export](../data/events-01.csv) at row 4 and [the second export](../data/events-02.csv) at row 2. Counting both records would turn five distinct aborts into six. The analyser stores one event with both source references.

The exports also disagree on when `PROFILE-588` cleared. Both rows go to quarantine. Accepting either disputed row would raise the profile reload count from two to three aborts. The conflict remains visible in the report for review.

Of **23 input rows**, the analyser keeps 16 distinct events and three additional source references for exact repeats. It quarantines four rows. Two carry the disputed clear times. The other two specify an unknown station or a clear time before the start.

The import validates station names, event IDs, fault codes and UTC timestamps. It keeps an event with an unknown clear time and leaves its duration unknown. In the example, `ABORT-652` still contributes to the five-abort count, and `ABORT-639` records a 157-second interval across midnight.

## Compare the events before each abort

The analyser looks for events at other stations during the 240 seconds leading up to each abort. It counts a condition once per abort. For example, two fixture contact checks appear before `ABORT-624` and contribute one to the tally.

| Earlier condition | Aborts preceded |
| --- | ---: |
| Fixture contact check | 4 / 5 |
| Programmer profile reload | 2 / 5 |
| Programmer session retry | 2 / 5 |

Contact check and profile reload appeared together before two aborts. Contact check and session retry appeared together before one. The analyser counts a pair only when both conditions precede the same abort.

Three records show where the window starts and ends.

- `CONTACT-463` starts exactly 240 seconds before `ABORT-652` and counts.
- `CONTACT-457` starts at the same second as `ABORT-639`. The timestamp supplies no ordering evidence.
- `RETRY-844` starts 241 seconds before `ABORT-667` and falls outside the window.

## Next check

The supplied [practice assessment](../data/practice-review.json) records insufficient evidence. It calls for running a reference module through the qualification cycle and comparing the programmer session log with the bench abort record.

The count measures how often a contact check appeared before an abort in this fixture. Estimating how often the check is followed by an abort requires comparable periods with completed cycles and adequate log coverage.

## Verification

The fixture generator defines every event and the practice assessment. The [Python analyser](../analytics.py) records accepted events and their sources, quarantined rows, timing, and condition counts in JSON. The [chart script](../scripts/render_investigation.py) draws the figure from that JSON file.

Run `make demo` to regenerate the reports. Run `make check` to test reconciliation, source pointers, lookback boundaries and report reproduction. [Fixture generator](../scripts/generate_fixture.py) · [Tests](../tests/test_analytics.py)

## Reporting and ML evaluation

A future reporting model could keep distinct events, source rows and calendar-day durations in separate tables. Source rows would support drill-through without multiplying event counts. Splitting a known interval at midnight would preserve its recorded duration. Whole-cell downtime would require a separate definition of cell state because equipment intervals can overlap.

Three possible experiments would use different targets and baselines.

- **Unusual episodes.** Compare an anomaly ranking with simple ordering by duration or recurrence.
- **Investigation priority.** Predict which findings reviewers mark worth checking. Compare an interpretable classifier with ranking by event count at the same review budget.
- **Relationship review.** Compare a model that uses lead times and episode counts with episode-support and majority baselines. Train against explicit reviewer assessments of which relationships merit follow-up.

An evaluation would group cases that share source records and reserve a later period for testing. Features would use only information available at the review cutoff. Practice assessments, unresolved evidence and unreviewed cases would stay outside the supervised target.
