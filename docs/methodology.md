# Methodology

## CSV input contract

Each input file must have a distinct filename and the exact five-column header `event_id,station,code,start_utc,clear_utc`. The analyser reads CSVs in strict mode and validates rows before reconciling them.

- `event_id` must match `[A-Z]+-[0-9]+`.
- `station` must belong to the recognised set (`test_bench`, `programmer`, `fixture_station`).
- `code` must match `[A-Z][A-Z0-9_]{1,31}`.
- `start_utc` is required, `clear_utc` is optional, and a non-empty clear time must be at or after the start time.

The analyser rejects a batch with an unexpected header. Individual rows that fail field validation enter quarantine with a reason and their source location.

## Canonical events and source origins

Accepted rows are represented as immutable canonical events separate from their source origins. Each origin records the CSV filename and the `csv.DictReader.line_num` value so blank lines in an export remain reflected in the row pointer.

When an identical event payload appears across multiple exports, the analyser keeps one canonical event and appends each additional origin.

## Conflicting versions

The analyser sorts batches by filename and groups valid rows by `event_id`. It compares every version of an event before accepting it.

If any field differs, every competing row for that identifier enters quarantine with a `conflict` kind. Holding every competing version keeps the reconciled output independent of file import order and surfaces source-log discrepancies in the JSON evidence.

## Explicit UTC and duration handling

All timestamps must be explicit UTC strings at second precision (`YYYY-MM-DDTHH:MM:SSZ`). Ambiguous local timestamps and sub-second formats are rejected.

Two duration edge cases are accepted because their start timestamps are valid and unambiguous.

- Overnight intervals such as `ABORT-639` (`2042-10-15T23:59:37Z` to `2042-10-16T00:02:14Z`) yield an exact UTC duration of 157 seconds.
- Open or unrecorded clear times such as `ABORT-652` emit `cleared_at` and `duration_seconds` as `null` while remaining eligible for start-based lookback comparisons.

## Episode window and pair counting

The investigation targets `test_bench` / `CYCLE_ABORT` episodes ordered by `(start, event_id)`. For each target episode, a candidate event qualifies when it comes from a different station and satisfies `0 < lead_seconds <= 240`, where `lead_seconds` is the target start minus the candidate start.

- Each preceding condition counts at most once per target episode. Before `ABORT-624`, `CONTACT-437` (238 seconds earlier) and `CONTACT-442` (38 seconds earlier) together add one episode to `fixture_station` / `CONTACT_CHECK` support.
- Same-episode pairs are formed from the deduplicated set of preceding conditions within each episode lookback.
- Three fixture events test the exact boundaries. `CONTACT-463` starts 240 seconds before `ABORT-652` and is included, `CONTACT-457` starts at the exact same second as `ABORT-639` (`2042-10-15T23:59:37Z`) and is excluded, and `RETRY-844` starts 241 seconds before `ABORT-667` and falls outside the window.

## Reproduce the fixture results

The [fixture generator](../scripts/generate_fixture.py) defines the input rows and review note. The [analyser](../analytics.py) writes the investigation reports, and the [comparison script](../scripts/evaluate_reconciliation.py) reruns the count and disputed-record checks. The [chart script](../scripts/render_investigation.py) renders the timing figure from the investigation JSON.

`make demo` regenerates the three reports in `outputs/demo/`. `make check` tests row counts, source pointers, timing boundaries and byte-for-byte reproduction of the [brief](../report/example-report.md), [investigation data](../report/example-report.json) and [comparison result](../report/reconciliation-check.json).

## Proposed reporting and ML evaluation

### Reporting grain plan

A future reporting layer would separate event, source-origin, and calendar-day tables into distinct grains. Event counts belong to the distinct-event table, while source-origin rows support drill-through back to raw batches without multiplying counts. A daily duration measure can split known intervals across UTC midnight boundaries and verify that daily slices sum to the original recorded seconds.

Recorded equipment intervals can overlap across stations. Estimating whole-cell downtime requires an explicit cell-state definition and sufficient telemetry coverage to establish unavailability. Versioned exports and stable event identifiers would allow a BI model to reconcile its measures against a fixed input snapshot.

### Future ML evaluation plan

Each proposed experiment needs its own review target and a baseline for comparison.

- Unusual-episode ranking would score atypical event patterns and compare against simple ordering by duration or recurrence, checking whether top-ranked episodes surface inspections an engineer considers useful.
- Investigation priority would learn which findings reviewers explicitly mark worth checking, starting with an interpretable classifier compared against a count-based rule under the same review budget.
- Relationship plausibility would train on explicit reviewer assessments of whether a candidate relationship merits follow-up, comparing lead-time and support features against simple episode-support and majority baselines.

Practice assessments, unresolved evidence, and unreviewed findings must stay outside any supervised target. Evaluation splits should group related conditions and shared source entries together. For later-period evaluation, features must use only records available at the intended review cutoff, reporting comparison population, review budget, missed examples, and variation across conditions. Forecasting future physical failures would require a separate prediction horizon and independently established outcomes.
