# Example investigation — synthetic data

23 export rows reconciled to 16 unique accepted events. 3 replay rows retain source references. Quarantine contains 2 conflicting and 2 invalid rows.

## Qualification-cycle aborts

Starts within the preceding 240 seconds count once per condition per episode. Paired conditions must occur in the same lookback. Tied starts are excluded.

| Other-station condition | Episodes supported |
| --- | ---: |
| fixture_station / `CONTACT_CHECK` | 4 / 5 |
| programmer / `PROFILE_RELOAD` | 2 / 5 |
| programmer / `SESSION_RETRY` | 2 / 5 |

| Same-episode pair | Episodes supported |
| --- | ---: |
| fixture_station / `CONTACT_CHECK` + programmer / `PROFILE_RELOAD` | 2 / 5 |
| fixture_station / `CONTACT_CHECK` + programmer / `SESSION_RETRY` | 1 / 5 |

## Source-linked episodes

- **ABORT-610** at 2042-10-14T16:37:19Z (30 s recorded interval). events-01.csv row 4, events-02.csv row 2.
  - CONTACT-431 · fixture_station / `CONTACT_CHECK`, 192 s earlier. events-01.csv row 2.
  - RETRY-817 · programmer / `SESSION_RETRY`, 64 s earlier. events-01.csv row 3.
- **ABORT-624** at 2042-10-14T17:11:42Z (42 s recorded interval). events-01.csv row 8.
  - CONTACT-437 · fixture_station / `CONTACT_CHECK`, 238 s earlier. events-01.csv row 5, events-02.csv row 3.
  - PROFILE-571 · programmer / `PROFILE_RELOAD`, 105 s earlier. events-01.csv row 6.
  - CONTACT-442 · fixture_station / `CONTACT_CHECK`, 38 s earlier. events-01.csv row 7.
- **ABORT-639** at 2042-10-15T23:59:37Z (157 s recorded interval). events-01.csv row 10.
  - RETRY-826 · programmer / `SESSION_RETRY`, 88 s earlier. events-01.csv row 9, events-02.csv row 4.
- **ABORT-652** at 2042-10-16T07:03:51Z (clear time unknown). events-02.csv row 7.
  - CONTACT-463 · fixture_station / `CONTACT_CHECK`, 240 s earlier. events-02.csv row 5.
  - PROFILE-593 · programmer / `PROFILE_RELOAD`, 127 s earlier. events-02.csv row 6.
- **ABORT-667** at 2042-10-16T09:42:08Z (12 s recorded interval). events-02.csv row 10.
  - CONTACT-479 · fixture_station / `CONTACT_CHECK`, 32 s earlier. events-02.csv row 9.

## Practice review

The assessment was **insufficient evidence**.

Run a reference module through the qualification cycle and compare the programmer session log with the bench abort record.

The timing evidence supports a follow-up check. Establishing a cause or prediction performance requires separate evidence.
