"""TPA feed simulator: 3 TPAs x 30 business days of claim files, with planted defects and an answer key.

What it produces (all under settings.yaml -> simulation.output_dir, gitignored):
    deliveries/<seq>_<tpa>_<date>_<kind>/   one folder per delivery: the data file + _manifest.json
    deliveries.csv                           the replay schedule: when each delivery "arrives"
    answer_key/file_defects.csv              every planted file-level problem
    answer_key/row_defects.csv               every planted row-level problem (file, line, rule)
    answer_key/summary.json                  counts per defect type, to grade against
And a few clean rows per TPA in simulation.sample_dir (committed, shown in the README).

Why deliveries and not just files:
    A TPA can send the same business date more than once (a duplicate, a corrected resend).
    Each delivery keeps its own folder, so a resend never overwrites the original: the landing
    zone stays an audit trail of exactly what arrived, and when.

Usage:
    python -m src.generators.tpa_feed_simulator            # full volume, ~75,000 rows
    python -m src.generators.tpa_feed_simulator --scale 0.1  # 10% of the rows (fast)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from itertools import count
from pathlib import Path
from typing import Any

from src.common.business_calendar import business_dates, deadline_for, local_datetime, next_business_day
from src.common.logging_utils import get_logger
from src.common.settings import REPO_ROOT, contract_columns, contract_table, master_data, settings
from src.generators.claims import ClaimPortfolio, build_fleet
from src.generators.defects import FileKey, RowDefectPlanter, blank_vins
from src.generators.feed_files import build_manifest, file_name, render_csv, render_manifest

LOGGER = get_logger(__name__)

# Arrival times are stored in UTC, the way S3 stamps objects (timezone.utc keeps Python 3.10 support)
UTC = timezone.utc

# Kinds of delivery (protocol constants, written to deliveries.csv)
ORIGINAL, CORRECTED, DUPLICATE_COPY = "ORIGINAL", "CORRECTED", "DUPLICATE_COPY"


@dataclass(frozen=True)
class Delivery:
    """One drop of a data file + manifest by a TPA, at a simulated arrival time."""

    tpa_id: str
    business_date: date
    kind: str  # ORIGINAL, CORRECTED or DUPLICATE_COPY
    arrival: datetime  # aware, UTC
    deadline: datetime  # aware, Central Time
    file_name: str
    text: str
    manifest: dict[str, Any]


@dataclass(frozen=True)
class FileDefect:
    """One planted file-level problem, as written to the answer key."""

    tpa_id: str
    business_date: str
    file_name: str
    defect: str
    expected_detection: str
    detail: str


@dataclass
class Simulation:
    """Everything the simulator builds before writing it to disk."""

    deliveries: list[Delivery] = field(default_factory=list)
    file_defects: list[FileDefect] = field(default_factory=list)
    row_defects: list[dict[str, Any]] = field(default_factory=list)
    clean_rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # sample rows per TPA


def by_tpa_and_day(entries: list[dict[str, Any]], dates: list[date]) -> dict[FileKey, dict[str, Any]]:
    """Index a defect list from settings.yaml by (tpa_id, business_date), translating day numbers to dates."""
    return {(entry["tpa_id"], dates[entry["day"] - 1]): entry for entry in entries}


def generate_rows(
    cfg: dict[str, Any], master: dict[str, Any], dates: list[date], rng: random.Random, scale: float
) -> dict[FileKey, list[dict[str, Any]]]:
    """Every TPA's clean rows for every business date.

    Args:
        cfg: settings.yaml.
        master: master_data.yaml.
        dates: The simulated business dates.
        rng: The seeded random generator.
        scale: Share of the configured volume (1.0 = full; tests use less).

    Returns:
        Rows per (tpa_id, business_date), in export order.
    """
    sim = cfg["simulation"]
    fleet = build_fleet(rng, master["fleet"])
    claim_numbers = count(1)  # Northbridge's claim counter, shared by the three TPAs
    files: dict[FileKey, list[dict[str, Any]]] = {}
    for tpa in master["tpas"]:
        # Scale the portfolio and the daily volumes together, so a small run keeps the same shape
        scaled = {
            **tpa,
            **{k: max(1, round(tpa[k] * scale)) for k in ("daily_rows", "open_claims_at_start", "new_claims_per_day")},
        }
        portfolio = ClaimPortfolio(
            tpa=scaled,
            coverages=master["coverages"],
            transaction_types=master["transaction_types"],
            fleet=fleet,
            sim=sim,
            timezone=cfg["calendar"]["timezone"],
            rng=rng,
            claim_numbers=claim_numbers,
            claim_id_prefix=master["company"]["claim_id_prefix"],
        )
        portfolio.seed_portfolio(dates[0], scaled["open_claims_at_start"])
        for day in dates:
            # Daily volume varies around the TPA's average (jitter from settings.yaml)
            jitter = 1 + rng.uniform(-sim["volume_jitter"], sim["volume_jitter"])
            files[(tpa["tpa_id"], day)] = portfolio.day_rows(day, round(scaled["daily_rows"] * jitter))
    return files


def normal_arrival(day: date, cfg: dict[str, Any], rng: random.Random) -> datetime:
    """A normal, on-time arrival: a random minute in the arrival window on the next business day (UTC)."""
    start, end = cfg["simulation"]["arrival_window_local"]
    tz = cfg["calendar"]["timezone"]
    first = local_datetime(next_business_day(day), start, tz)
    last = local_datetime(next_business_day(day), end, tz)
    return (first + timedelta(minutes=rng.randint(0, int((last - first).total_seconds() // 60)))).astimezone(UTC)


class DeliveryBuilder:
    """Builds the deliveries of every file, applying the file-level defects from settings.yaml."""

    def __init__(self, cfg: dict[str, Any], master: dict[str, Any], dates: list[date], rng: random.Random):
        """Read the defect plan and the contract's file layout.

        Args:
            cfg: settings.yaml.
            master: master_data.yaml.
            dates: The simulated business dates (day numbers in settings.yaml are 1-based indexes).
            rng: The seeded random generator.
        """
        self.cfg, self.rng, self.dates = cfg, rng, dates
        defects = cfg["defects"]
        self.late = by_tpa_and_day(defects["late_files"], dates)
        self.missing = by_tpa_and_day(defects["missing_files"], dates)
        self.drift = by_tpa_and_day(defects["schema_drift"], dates)
        self.mismatch = by_tpa_and_day(defects["manifest_mismatch"], dates)
        self.duplicates = by_tpa_and_day(defects["duplicate_resends"], dates)
        self.delimiters = {tpa["tpa_id"]: tpa["delimiter"] for tpa in master["tpas"]}
        self.columns = contract_columns(cfg["contract"]["data_table"])
        self.name_pattern = contract_table(cfg["contract"]["data_table"])["physicalName"]
        self.file_defects: list[FileDefect] = []

    def rejected_before_rows(self) -> set[FileKey]:
        """Files whose ORIGINAL is rejected as a whole (row defects are never planted in them)."""
        return set(self.drift) | set(self.mismatch)

    def record_defect(self, key: FileKey, name: str, defect: str, expected: str, detail: str) -> None:
        """Write one file-level answer-key record."""
        self.file_defects.append(FileDefect(key[0], key[1].isoformat(), name, defect, expected, detail))

    def _arrival(self, key: FileKey, deadline: datetime, name: str) -> datetime:
        """When the ORIGINAL delivery arrives: on time, late or missing, per the defect plan."""
        tz = self.cfg["calendar"]["timezone"]
        if key in self.late:
            # Late: a fixed local time after the deadline, on the deadline's day
            local = self.late[key]["arrival_local"]
            self.record_defect(key, name, "LATE_FILE", "SLA_BREACH_ARRIVAL", f"arrived {local} CT, deadline 06:00 CT")
            return local_datetime(deadline.date(), local, tz).astimezone(UTC)
        if key in self.missing:
            # Missing at the deadline: nothing arrives until many hours later
            hours = self.missing[key]["hours_late"]
            self.record_defect(
                key, name, "MISSING_FILE", "ALERT_WARNING_06_AND_CRITICAL_08", f"arrived {hours} h after the deadline"
            )
            return (deadline + timedelta(hours=hours)).astimezone(UTC)
        return normal_arrival(key[1], self.cfg, self.rng)

    def build(self, key: FileKey, rows: list[dict[str, Any]]) -> list[Delivery]:
        """Every delivery for one file: the original and, when planned, a duplicate copy or a corrected resend.

        Args:
            key: (tpa_id, business_date).
            rows: The file's final rows (row defects already planted).

        Returns:
            One to two deliveries.
        """
        tpa_id, day = key
        cal = self.cfg["calendar"]
        deadline = deadline_for(day, cal["deadline_local_time"], cal["timezone"])
        name = file_name(self.name_pattern, tpa_id, day)
        delimiter = self.delimiters[tpa_id]

        # The correct file and its truthful manifest
        text = render_csv(rows, self.columns, delimiter)
        manifest = build_manifest(tpa_id, day, name, text, rows)
        arrival = self._arrival(key, deadline, name)

        def delivery(kind: str, when: datetime, body: str, receipt: dict) -> Delivery:
            return Delivery(tpa_id, day, kind, when, deadline, name, body, receipt)

        if key in self.drift:
            # Schema drift: the original renames a column (rejected), then the TPA resends the correct layout
            plan = self.drift[key]
            renamed = [plan["renamed_to"] if c == plan["renamed_from"] else c for c in self.columns]
            bad_rows = [{plan["renamed_to"] if k == plan["renamed_from"] else k: v for k, v in r.items()} for r in rows]
            bad_text = render_csv(bad_rows, renamed, delimiter)
            bad_manifest = {**manifest, "sha256": build_manifest(tpa_id, day, name, bad_text, rows)["sha256"]}
            detail = (
                f"{plan['renamed_from']} renamed to {plan['renamed_to']}; "
                f"corrected file {plan['resend_after_hours']} h later"
            )
            self.record_defect(key, name, "SCHEMA_DRIFT", "REJECT_FILE", detail)
            later = arrival + timedelta(hours=plan["resend_after_hours"])
            return [delivery(ORIGINAL, arrival, bad_text, bad_manifest), delivery(CORRECTED, later, text, manifest)]

        if key in self.mismatch:
            # Manifest mismatch: the receipt does not describe the file (rejected), then a corrected pair follows
            plan = self.mismatch[key]
            wrong = dict(manifest)
            if plan["field"] == "row_count":
                wrong["row_count"] = manifest["row_count"] + plan["offset"]
            else:
                # Decimal, not float: the offset must be exactly $1,284.50, not $1,284.4999...
                wrong["control_total_paid"] = (
                    f"{Decimal(manifest['control_total_paid']) + Decimal(str(plan['offset'])):.2f}"
                )
            detail = f"{plan['field']} off by {plan['offset']}; corrected manifest {plan['resend_after_hours']} h later"
            self.record_defect(key, name, f"MANIFEST_{plan['field'].upper()}_MISMATCH", "REJECT_FILE", detail)
            later = arrival + timedelta(hours=plan["resend_after_hours"])
            return [delivery(ORIGINAL, arrival, text, wrong), delivery(CORRECTED, later, text, manifest)]

        if key in self.duplicates:
            # Duplicate resend: byte-for-byte the same file again, so the SHA-256 is identical
            hours = self.duplicates[key]["resend_after_hours"]
            self.record_defect(
                key, name, "DUPLICATE_RESEND", "IGNORE_AND_LOG", f"same SHA-256 sent again {hours} h later"
            )
            later = arrival + timedelta(hours=hours)
            return [delivery(ORIGINAL, arrival, text, manifest), delivery(DUPLICATE_COPY, later, text, manifest)]

        return [delivery(ORIGINAL, arrival, text, manifest)]


def apply_completeness_drift(
    cfg: dict[str, Any],
    files: dict[FileKey, list[dict[str, Any]]],
    dates: list[date],
    rng: random.Random,
    builder: DeliveryBuilder,
) -> set[FileKey]:
    """Blank VINs on the configured TPA and days, and record each file in the answer key.

    Returns:
        The affected files (their originals are rejected: 18% is above 2x the 2% limit).
    """
    affected: set[FileKey] = set()
    for plan in cfg["defects"]["completeness_drift"]:
        for day in dates[plan["first_day"] - 1 : plan["last_day"]]:
            key = (plan["tpa_id"], day)
            blank = blank_vins(files[key], plan["vin_blank_rate"], rng)
            share = blank / len(files[key])
            name = file_name(builder.name_pattern, key[0], day)
            builder.record_defect(
                key, name, "COMPLETENESS_DRIFT", "COMPLETENESS_SLA_BREACH", f"vin blank on {share:.1%} of rows"
            )
            affected.add(key)
    return affected


def simulate(cfg: dict[str, Any], master: dict[str, Any], scale: float = 1.0) -> Simulation:
    """Build every delivery and the answer key, in memory (nothing is written).

    Args:
        cfg: settings.yaml.
        master: master_data.yaml.
        scale: Share of the configured volume.

    Returns:
        The deliveries in arrival order, and the answer key.
    """
    rng = random.Random(cfg["simulation"]["seed"])
    cal = cfg["calendar"]
    dates = business_dates(date.fromisoformat(str(cal["first_business_date"])), cal["business_days"])

    # 1. Clean rows for every TPA and business date
    files = generate_rows(cfg, master, dates, rng, scale)

    # 2. File-level edits that change rows: a week of blank VINs at one TPA
    builder = DeliveryBuilder(cfg, master, dates, rng)
    drifted = apply_completeness_drift(cfg, files, dates, rng, builder)

    # 3. Row defects only in files that will be accepted, so none hides behind a rejected file
    rejected = builder.rejected_before_rows() | drifted
    eligible = [key for key in files if key not in rejected]
    row_defects = RowDefectPlanter(files, eligible, rng).plant_all(cfg["defects"]["row_defects"])

    # 4. Deliveries (originals, duplicate copies, corrected resends), in the order they arrive
    deliveries = [d for key, rows in files.items() for d in builder.build(key, rows)]
    deliveries.sort(key=lambda d: d.arrival)

    # 5. A few clean rows per TPA for the README: first business date, rows without planted defects
    planted = {(d.tpa_id, d.business_date, d.line_number) for d in row_defects}
    samples = {
        tpa["tpa_id"]: [
            row
            for i, row in enumerate(files[(tpa["tpa_id"], dates[0])])
            if (tpa["tpa_id"], dates[0].isoformat(), i + 2) not in planted
        ][: cfg["simulation"]["sample_rows"]]
        for tpa in master["tpas"]
    }
    return Simulation(deliveries, builder.file_defects, [d.as_dict() for d in row_defects], samples)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a list of dicts as a CSV with a header (answer key, schedule)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(result: Simulation) -> dict[str, Any]:
    """Counts the grading compares against: deliveries by kind, file and row defects by type."""
    return {
        "deliveries": len(result.deliveries),
        "deliveries_by_kind": dict(Counter(d.kind for d in result.deliveries)),
        "expected_files": len({(d.tpa_id, d.business_date) for d in result.deliveries}),
        "rows_delivered_in_originals": sum(d.manifest["row_count"] for d in result.deliveries if d.kind == ORIGINAL),
        "file_defects": dict(Counter(d.defect for d in result.file_defects)),
        "row_defects": dict(Counter(d["defect"] for d in result.row_defects)),
    }


def write_outputs(
    result: Simulation, cfg: dict[str, Any], master: dict[str, Any], out_dir: Path, sample_dir: Path
) -> dict:
    """Write deliveries, the schedule, the answer key and the README samples.

    Returns:
        The summary that was written to answer_key/summary.json.
    """
    # Start from an empty folder, so files from an earlier run never mix with this one
    if out_dir.exists():
        shutil.rmtree(out_dir)
    schedule = []
    tz = cfg["calendar"]["timezone"]
    for seq, d in enumerate(result.deliveries, start=1):
        # One folder per delivery: the data file and its manifest, exactly as the TPA sends them
        folder = out_dir / "deliveries" / f"{seq:03d}_{d.tpa_id}_{d.business_date:%Y%m%d}_{d.kind}"
        folder.mkdir(parents=True)
        (folder / d.file_name).write_text(d.text, encoding="utf-8")
        (folder / cfg["contract"]["manifest_file_name"]).write_text(render_manifest(d.manifest), encoding="utf-8")
        schedule.append(
            {
                "seq": seq,
                "tpa_id": d.tpa_id,
                "business_date": d.business_date.isoformat(),
                "kind": d.kind,
                "arrival_utc": d.arrival.isoformat().replace("+00:00", "Z"),
                "arrival_local": d.arrival.astimezone(d.deadline.tzinfo).isoformat(),
                "deadline_local": d.deadline.isoformat(),
                "file_name": d.file_name,
                "folder": folder.relative_to(out_dir).as_posix(),
                "sha256": d.manifest["sha256"],
            }
        )
    write_csv(out_dir / "deliveries.csv", schedule)

    # The answer key: local only, never uploaded (it would let the monitor "cheat")
    write_csv(out_dir / "answer_key" / "file_defects.csv", [vars(d) for d in result.file_defects])
    write_csv(out_dir / "answer_key" / "row_defects.csv", result.row_defects)
    summary = summarize(result)
    (out_dir / "answer_key" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # README samples: a few clean rows per TPA, in its own delimiter
    columns = contract_columns(cfg["contract"]["data_table"])
    for tpa in master["tpas"]:
        rows = result.clean_rows[tpa["tpa_id"]]
        sample_dir.mkdir(parents=True, exist_ok=True)
        (sample_dir / f"{tpa['tpa_id']}_claims_sample.csv").write_text(
            render_csv(rows, columns, tpa["delimiter"]), encoding="utf-8"
        )
    LOGGER.info("simulation written", extra={"fields": {"out_dir": str(out_dir), "timezone": tz, **summary}})
    return summary


def main(argv: list[str] | None = None) -> None:
    """Command line: simulate and write everything to the configured folders."""
    parser = argparse.ArgumentParser(description="Simulate the TPA claim feeds with planted defects.")
    parser.add_argument("--scale", type=float, default=1.0, help="share of the configured volume (default 1.0)")
    parser.add_argument("--out", type=Path, default=None, help="default: settings.yaml -> simulation.output_dir")
    args = parser.parse_args(argv)

    cfg, master = settings(), master_data()
    out_dir = args.out or REPO_ROOT / cfg["simulation"]["output_dir"]
    summary = write_outputs(
        simulate(cfg, master, args.scale), cfg, master, out_dir, REPO_ROOT / cfg["simulation"]["sample_dir"]
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
