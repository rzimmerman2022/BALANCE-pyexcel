# Manual Header Validation

This document records the results of manually checking a sample of real bank CSV exports against the current `schema_registry.yml`.

## Checked Files (May 2025)

- `CSVs/Jordyn/BALANCE - Jordyn PDF - 2024-06.csv`
- `sample_data_multi/Jordyn/Jordyn - Chase Bank - Total Checking x6173 - All.csv`
- `sample_data_multi/Jordyn/Jordyn - Discover - Discover It Card x1544 - CSV.csv`
- `sample_data_multi/Jordyn/Jordyn - Wells Fargo - Active Cash Visa Signature Card x4296 - CSV.csv`
- `sample_data_multi/Ryan/BALANCE - Monarch Money - 041225.csv`
- `sample_data_multi/Ryan/BALANCE - Rocket Money - 041225.csv`

Each file's header row was compared to the corresponding schema definition. All headers matched the expected `header_signature` entries.

## Remaining Unmatched Headers

None. Every tested CSV aligned with a schema in `rules/schema_registry.yml`.

These results clear the path for upcoming Stage‑3 refactors.
