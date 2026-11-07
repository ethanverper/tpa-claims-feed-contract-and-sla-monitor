"""Turn rows into the exact bytes a TPA delivers: the data file plus its manifest.

What a delivery is:
    One data file (CSV, or pipe-delimited for TPA-B) and one `_manifest.json`, the receipt that
    says how many rows the file has, what they add up to, and the file's SHA-256 fingerprint.
    The manifest lets the receiver prove the file arrived complete and unchanged: if one row is
    lost in transfer, the count no longer matches; if one byte changes, the fingerprint does not.

Why reading lives here too: writing and reading the same format side by side keeps them in
agreement, and the tests use `read_rows()` to prove every clean file matches its own manifest.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date
from decimal import Decimal
from typing import Any

# The column the manifest's control total is computed from (named in the data contract)
CONTROL_TOTAL_COLUMN = "paid_amount"


def file_name(pattern: str, tpa_id: str, business_date: date) -> str:
    """The data file's name, from the contract's physicalName pattern.

    Args:
        pattern: e.g. "{tpa_id}_claims_{YYYYMMDD}.csv" (docs/data-contract.yaml).
        tpa_id: e.g. "TPA-A".
        business_date: The date the file covers.

    Returns:
        e.g. "TPA-A_claims_20261001.csv".
    """
    return pattern.replace("{YYYYMMDD}", f"{business_date:%Y%m%d}").replace("{tpa_id}", tpa_id)


def render_csv(rows: list[dict[str, Any]], columns: list[str], delimiter: str) -> str:
    """The data file's text: header, then one line per row, in contract column order.

    Args:
        rows: Rows keyed by column name.
        columns: Header names in order (a renamed column here produces the schema-drift defect).
        delimiter: "," or "|" (per TPA, master_data.yaml).

    Returns:
        The file content with "\\n" line endings.
    """
    buffer = io.StringIO()
    # extrasaction="raise": a row with a key outside the header is a bug in the simulator, not data
    writer = csv.DictWriter(buffer, fieldnames=columns, delimiter=delimiter, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def read_rows(text: str, delimiter: str) -> list[dict[str, str]]:
    """Parse a data file back into rows (no validation: that is the checker's job, level 2)."""
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def sha256_of(text: str) -> str:
    """The file's fingerprint: SHA-256 of its UTF-8 bytes, as 64 hex characters."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def control_total(rows: list[dict[str, Any]], column: str = CONTROL_TOTAL_COLUMN) -> Decimal:
    """Sum of the paid amounts, exact to the cent.

    Why Decimal: adding 1,200 two-decimal amounts as floats can drift by a cent, and a one-cent
    difference would make a correct file fail its own control-total check.
    """
    return sum((Decimal(row[column]) for row in rows), Decimal("0"))


def build_manifest(tpa_id: str, business_date: date, name: str, text: str, rows: list[dict[str, Any]]) -> dict:
    """The manifest that truthfully describes one data file.

    Args:
        tpa_id: Who sends the file.
        business_date: The date it covers.
        name: The data file's name.
        text: The data file's exact content (the fingerprint is computed on it).
        rows: The rows in the file (for the count and the control total).

    Returns:
        A dict with the six manifest fields of the data contract.
    """
    return {
        "tpa_id": tpa_id,
        "business_date": business_date.isoformat(),
        "file_name": name,
        "row_count": len(rows),
        "control_total_paid": f"{control_total(rows):.2f}",
        "sha256": sha256_of(text),
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    """The manifest file's text: pretty JSON, keys in contract order."""
    return json.dumps(manifest, indent=2) + "\n"
