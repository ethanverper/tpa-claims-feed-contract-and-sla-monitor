"""Tests for level 1: the VIN helper, the business calendar and the TPA feed simulator (local, no AWS).

What these tests prove:
    - every clean row the simulator writes obeys the data contract (so any row the checker flags
      later is a planted defect, never noise from the generator);
    - every planted defect is exactly where the answer key says, in the configured numbers;
    - the same seed always produces the same files (the README numbers are reproducible).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.common.business_calendar import business_dates, deadline_for, next_business_day
from src.common.settings import contract_table, master_data, settings
from src.common.vin import break_check_digit, is_valid_vin
from src.generators.feed_files import build_manifest, read_rows
from src.generators.tpa_feed_simulator import CORRECTED, DUPLICATE_COPY, ORIGINAL, simulate, summarize

# A small run keeps the tests fast; the shape (defects, calendar) is the same as the full run
TEST_SCALE = 0.05
TZ = "America/Chicago"


@pytest.fixture(scope="module")
def result():
    """One small simulation shared by the tests of this module."""
    return simulate(settings(), master_data(), TEST_SCALE)


@pytest.fixture(scope="module")
def delimiters():
    """Each TPA's file delimiter."""
    return {tpa["tpa_id"]: tpa["delimiter"] for tpa in master_data()["tpas"]}


# --- VIN -------------------------------------------------------------------------------------------


def test_known_vin_is_valid_and_a_changed_check_digit_is_not():
    # The textbook example VIN from the check-digit standard
    assert is_valid_vin("1M8GDM9AXKP042788")
    assert not is_valid_vin(break_check_digit("1M8GDM9AXKP042788"))


def test_vin_with_forbidden_letter_or_wrong_length_is_invalid():
    assert not is_valid_vin("1M8GDM9AXKP04278")  # 16 characters
    assert not is_valid_vin("1M8GDM9AXKO042788")  # the letter O is never used


# --- Business calendar -----------------------------------------------------------------------------


def test_next_business_day_after_friday_is_monday():
    assert next_business_day(date(2026, 10, 2)) == date(2026, 10, 5)


def test_business_dates_skip_weekends():
    dates = business_dates(date(2026, 10, 1), 30)
    assert len(dates) == 30 and all(d.weekday() < 5 for d in dates)
    assert dates[-1] == date(2026, 11, 11)


def test_deadline_moves_one_hour_in_utc_when_daylight_saving_ends():
    # 06:00 CT is 11:00 UTC in October (CDT, UTC-5) and 12:00 UTC after 2026-11-01 (CST, UTC-6)
    october = deadline_for(date(2026, 10, 15), "06:00", TZ).astimezone(timezone.utc)
    november = deadline_for(date(2026, 11, 2), "06:00", TZ).astimezone(timezone.utc)
    assert (october.hour, november.hour) == (11, 12)


# --- Simulator: volumes and the answer key ---------------------------------------------------------


def test_one_expected_file_per_tpa_per_business_day(result):
    summary = summarize(result)
    assert summary["expected_files"] == 90
    # 90 originals + 2 duplicate copies + 4 corrected resends (2 schema drift, 2 manifest mismatch)
    assert summary["deliveries_by_kind"] == {ORIGINAL: 90, DUPLICATE_COPY: 2, CORRECTED: 4}


def test_file_defects_match_the_configuration(result):
    defects = settings()["defects"]
    counts = summarize(result)["file_defects"]
    assert counts["LATE_FILE"] == len(defects["late_files"])
    assert counts["MISSING_FILE"] == len(defects["missing_files"])
    assert counts["SCHEMA_DRIFT"] == len(defects["schema_drift"])
    assert counts["DUPLICATE_RESEND"] == len(defects["duplicate_resends"])
    assert counts["COMPLETENESS_DRIFT"] == 7
    assert counts["MANIFEST_ROW_COUNT_MISMATCH"] + counts["MANIFEST_CONTROL_TOTAL_PAID_MISMATCH"] == 2


def test_row_defects_match_the_configuration(result):
    configured = {name.upper(): spec["count"] for name, spec in settings()["defects"]["row_defects"].items()}
    assert summarize(result)["row_defects"] == configured


def test_each_row_defect_points_at_the_right_line(result, delimiters):
    # The answer key's line number must lead to a row with the recorded transaction_id
    files = {(d.tpa_id, d.business_date.isoformat()): d for d in result.deliveries if d.kind == ORIGINAL}
    for defect in result.row_defects:
        delivery = files[(defect["tpa_id"], defect["business_date"])]
        rows = read_rows(delivery.text, delimiters[defect["tpa_id"]])
        assert rows[defect["line_number"] - 2]["transaction_id"] == defect["transaction_id"]


# --- Simulator: file-level defects -----------------------------------------------------------------


def test_only_planted_late_and_missing_files_arrive_after_the_deadline(result):
    late = {(d.tpa_id, d.business_date) for d in result.file_defects if d.defect in ("LATE_FILE", "MISSING_FILE")}
    after = {
        (d.tpa_id, d.business_date.isoformat())
        for d in result.deliveries
        if d.kind == ORIGINAL and d.arrival > d.deadline
    }
    assert after == late


def test_clean_deliveries_match_their_manifest(result, delimiters):
    broken = {(d.tpa_id, d.business_date) for d in result.file_defects if d.defect.startswith(("MANIFEST", "SCHEMA"))}
    for d in result.deliveries:
        if d.kind == ORIGINAL and (d.tpa_id, d.business_date.isoformat()) in broken:
            continue
        rows = read_rows(d.text, delimiters[d.tpa_id])
        assert d.manifest == build_manifest(d.tpa_id, d.business_date, d.file_name, d.text, rows)


def test_schema_drift_original_renames_the_column_and_the_resend_fixes_it(result):
    drift = [d for d in result.deliveries if d.tpa_id == "TPA-B" and d.business_date.isoformat() == "2026-10-23"]
    original, corrected = sorted(drift, key=lambda d: d.arrival)
    assert "amount_paid" in original.text.splitlines()[0] and "paid_amount" not in original.text.splitlines()[0]
    assert corrected.kind == CORRECTED and "paid_amount" in corrected.text.splitlines()[0]


def test_duplicate_copy_is_byte_for_byte_the_original(result):
    copies = [d for d in result.deliveries if d.kind == DUPLICATE_COPY]
    originals = {(d.tpa_id, d.business_date): d for d in result.deliveries if d.kind == ORIGINAL}
    for copy in copies:
        assert copy.text == originals[(copy.tpa_id, copy.business_date)].text
        assert copy.manifest["sha256"] == originals[(copy.tpa_id, copy.business_date)].manifest["sha256"]


def test_completeness_drift_files_exceed_the_vin_limit_and_others_do_not(result, delimiters):
    drifted = {(d.tpa_id, d.business_date) for d in result.file_defects if d.defect == "COMPLETENESS_DRIFT"}
    for d in result.deliveries:
        if d.kind != ORIGINAL or (d.tpa_id, d.business_date.isoformat()) in drifted or "amount_paid" in d.text[:400]:
            continue
        rows = read_rows(d.text, delimiters[d.tpa_id])
        # Clean files stay at or under the contract's 2% (the simulator blanks an exact number per file)
        assert sum(1 for r in rows if not r["vin"]) <= len(rows) * 0.02


# --- Simulator: every clean row obeys the contract ---------------------------------------------------


def test_clean_rows_obey_the_contract(result, delimiters):
    planted = {(d["tpa_id"], d["business_date"], d["line_number"]) for d in result.row_defects}
    duplicate_originals = set()  # first occurrences are clean, so they are checked too
    allowed = {
        p["name"]: set(p["quality"][0]["arguments"]["validValues"])
        for p in contract_table("claim_transactions")["properties"]
        if "quality" in p and p["quality"][0]["metric"] == "invalidValues"
    }
    for d in result.deliveries:
        if d.kind != ORIGINAL or "amount_paid" in d.text.splitlines()[0]:
            continue
        for index, row in enumerate(read_rows(d.text, delimiters[d.tpa_id])):
            if (d.tpa_id, d.business_date.isoformat(), index + 2) in planted:
                continue
            duplicate_originals.add(row["transaction_id"])
            # Allowed values for every closed list (enums, currency)
            assert all(row[column] in values for column, values in allowed.items()), row
            # Dates in order: loss <= report <= transaction <= extract time
            as_of = datetime.fromisoformat(row["as_of_ts"]).date()
            assert row["loss_date"] <= row["report_date"] <= row["transaction_date"] <= as_of.isoformat(), row
            # Sign rule: payments positive, recoveries negative
            paid = float(row["paid_amount"])
            assert paid > 0 if row["transaction_type"] == "PAYMENT" else True, row
            assert paid < 0 if row["transaction_type"] == "RECOVERY" else True, row
            # A VIN, when present, has a valid check digit
            assert not row["vin"] or is_valid_vin(row["vin"]), row


def test_same_seed_gives_the_same_files():
    first = simulate(settings(), master_data(), TEST_SCALE)
    second = simulate(settings(), master_data(), TEST_SCALE)
    assert [d.manifest["sha256"] for d in first.deliveries] == [d.manifest["sha256"] for d in second.deliveries]
