# Production Line Fault Analytics case study

Two exports for a fictional electronics test cell repeat some events and disagree on when one event cleared. This case measures how those rows affect the abort count and the conditions an engineer would inspect. The [fixture generator](../scripts/generate_fixture.py) defines the records and the practice review.

## Abort counts and disputed records

The controlled comparison in [evaluate_reconciliation.py](../scripts/evaluate_reconciliation.py) and [reconciliation-check.json](../report/reconciliation-check.json) measures both effects on the 23 rows across [events-01.csv](../data/events-01.csv) and [events-02.csv](../data/events-02.csv). Raw counting finds 7 rows carrying the `CYCLE_ABORT` label. Row validation removes `ABORT-659` (`events-01.csv` row 13, where clear precedes start), leaving 6 valid abort rows. Exact-repeat deduplication merges the two identical copies of `ABORT-610`, leaving 5 distinct abort episodes.

Event `PROFILE-588` appears in both exports with the same start time (`2042-10-16T09:40:29Z`) and conflicting clear times, `2042-10-16T09:41:04Z` in [events-01.csv](../data/events-01.csv) row 12 and `2042-10-16T09:40:53Z` in [events-02.csv](../data/events-02.csv) row 11. Holding both rows in quarantine keeps `programmer` / `PROFILE_RELOAD` at 2 of 5 episodes. If either version of `PROFILE-588` were admitted on its own, `PROFILE_RELOAD` support would rise to 3 of 5 episodes, putting it ahead of session retry, which precedes two aborts. Both versions have the same start time, so either would add the same third abort to the profile-reload count.

## Trace an abort to its source rows

Event `ABORT-610` has a 30-second recorded interval. It appears in [events-01.csv](../data/events-01.csv) at row 4 and again in [events-02.csv](../data/events-02.csv) at row 2.

In [analytics.py](../analytics.py), the canonical event payload is stored once while both `(batch, row)` pointers are attached to its `origins` list. Within the preceding 240 seconds, two other-station events qualify as earlier conditions for `ABORT-610`.

- `CONTACT-431` (`fixture_station` / `CONTACT_CHECK`) starts 192 seconds earlier in `events-01.csv` row 2.
- `RETRY-817` (`programmer` / `SESSION_RETRY`) starts 64 seconds earlier in `events-01.csv` row 3.

The same origin-retention rule applies to the other exact repeats (`CONTACT-437` and `RETRY-826`). The checked-in [example report](../report/example-report.md) lists every episode and preceding event with its source batch and row number, and the [JSON evidence package](../report/example-report.json) records every quarantined row alongside its rejection reason.

## Events before each abort

Across the five reconciled `CYCLE_ABORT` episodes, `fixture_station` / `CONTACT_CHECK` precedes 4 of 5 aborts, while `programmer` / `PROFILE_RELOAD` and `programmer` / `SESSION_RETRY` each precede 2 of 5. Same-episode pairs show `CONTACT_CHECK` + `PROFILE_RELOAD` before 2 of 5 aborts (`ABORT-624`, `ABORT-652`) and `CONTACT_CHECK` + `SESSION_RETRY` before 1 of 5 (`ABORT-610`).

[Event timing chart](../assets/fault-investigation.png)

[Timestamp and counting rules](methodology.md)

## Next check

The generated brief carries a supplied practice review from [practice-review.json](../data/practice-review.json) with an assessment of insufficient evidence. Its proposed next check is to run a reference module through the qualification cycle and compare the programmer session log with the bench abort record.

A preceding contact check can reflect a shared upstream step, routine fixture setup, or clock offset between devices. Estimating how often a check is followed by an abort would require comparable intervals with completed cycles and adequate log coverage.
