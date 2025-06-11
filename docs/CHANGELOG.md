## [0.3.0] – 2025-06-11
### Added
* Dual-mode ledger parser – supports standard `Date,Description,Amount` CSV _and_ single-column “vertical” export.
* Header-normalisation map extended (`running_balance`, rent portion columns).
* Zero-sum invariant check now fails fast if Ryan + Jordyn ≠ 0 after reconciliation.
* Fixture **vertical_ledger.csv** and unit test **test_ledger_parser** to guarantee vertical-format parsing remains green.

### Fixed
* Rent 43 / 57 split now applied only to rent rows.
* Leading/trailing-space headers in Expense CSV normalised.

### Internal
* Version bumped to **0.3.0** in `pyproject.toml`.
* All tests pass (23 total); baseline CLI yields Ryan + Jordyn = 0.00 with ≥ 90 % consistency.
