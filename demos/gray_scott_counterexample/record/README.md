# Curated immutable run record

These files were copied byte-for-byte from the completed local campaign
`artifacts/gray-scott-mvp-run-0001`. Files under `workspace/` are immutable and
their SHA-256 digests are recorded in `mvp_report.json`.

Included are the portable manifest, report, hypothesis ledger, claim summary,
artifact-provenance map, complete transcript, and all 22 generated workspace
files. The mutable `mvp_ledger.sqlite3` runtime database is intentionally
omitted: `hypothesis_ledger.json` is the public claim representation, and the
read-only monitor and TUI can project this record without SQLite.

From the repository root, verify the workspace with:

```bash
uv run python demos/gray_scott_counterexample/verify_record.py
```
