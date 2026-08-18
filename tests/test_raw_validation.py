from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.cli.validate_raw as validate_raw_cli
from src.validation.raw import (
    RawValidationReport,
    RawValidator,
    ValidationCheck,
)


START = date(2026, 1, 1)


def bare_validator():
    validator = RawValidator.__new__(
        RawValidator
    )
    validator.start_date = START
    return validator


def test_report_passes_only_when_all_checks_pass():
    good = RawValidationReport(
        checks=(
            ValidationCheck(
                "one",
                True,
                "ok",
            ),
            ValidationCheck(
                "two",
                True,
                "ok",
            ),
        )
    )

    bad = RawValidationReport(
        checks=(
            ValidationCheck(
                "one",
                True,
                "ok",
            ),
            ValidationCheck(
                "two",
                False,
                "bad",
            ),
        )
    )

    assert good.passed is True
    assert bad.passed is False


def test_history_detects_gap():
    validator = bare_validator()

    validator._rows = MagicMock(
        return_value=[
            (date(2026, 1, 1),),
            (date(2026, 1, 3),),
        ]
    )

    check = (
        validator
        ._check_simulation_history()
    )

    assert check.passed is False
    assert "missing=1" in check.details


def test_run_status_detects_failed_day():
    validator = bare_validator()

    validator._rows = MagicMock(
        return_value=[
            (
                date(2026, 1, 2),
                "failed",
            )
        ]
    )

    check = (
        validator
        ._check_run_statuses()
    )

    assert check.passed is False
    assert "non_success=1" in check.details


def test_run_counts_detect_mismatch():
    validator = bare_validator()

    validator._rows = MagicMock(
        side_effect=[
            [
                (
                    date(2026, 1, 1),
                    10,
                    100,
                )
            ],
            [
                (
                    date(2026, 1, 1),
                    10,
                )
            ],
            [
                (
                    date(2026, 1, 1),
                    99,
                )
            ],
        ]
    )

    check = validator._check_run_counts()

    assert check.passed is False
    assert "mismatches=1" in check.details


def test_app_version_detects_mismatch():
    validator = bare_validator()

    resolver = MagicMock()
    resolver.version_for_date.return_value = (
        "1.0"
    )

    validator.app_version_resolver = (
        resolver
    )

    validator._rows = MagicMock(
        side_effect=[
            [
                (
                    date(2026, 1, 1),
                    "9.9",
                    100,
                )
            ],
            [
                (
                    date(2026, 1, 1),
                    "1.0",
                    10,
                )
            ],
        ]
    )

    check = (
        validator
        ._check_app_versions()
    )

    assert check.passed is False
    assert (
        "mismatched_rows=100"
        in check.details
    )


def test_campaign_detects_mismatch():
    validator = bare_validator()

    resolver = MagicMock()
    resolver.campaign_id_for_channel.return_value = None

    validator.campaign_resolver = (
        resolver
    )

    validator._rows = MagicMock(
        return_value=[
            (
                date(2026, 1, 1),
                "organic",
                "wrong_campaign",
                3,
            )
        ]
    )

    check = validator._check_campaigns()

    assert check.passed is False
    assert (
        "mismatched_users=3"
        in check.details
    )


class FakeConnectionContext:
    def __init__(self):
        self.connection = MagicMock()

    def __enter__(self):
        return self.connection

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


def test_validate_raw_cli_success(
    monkeypatch,
    capsys,
):
    report = RawValidationReport(
        checks=(
            ValidationCheck(
                "check_one",
                True,
                "ok",
            ),
        )
    )

    monkeypatch.setattr(
        validate_raw_cli,
        "get_connection",
        lambda: FakeConnectionContext(),
    )

    validator = MagicMock()
    validator.validate.return_value = report

    monkeypatch.setattr(
        validate_raw_cli,
        "RawValidator",
        MagicMock(
            return_value=validator
        ),
    )

    validate_raw_cli.main()

    output = capsys.readouterr().out

    assert "PASS check_one" in output
    assert (
        "RAW VALIDATION PASSED"
        in output
    )


def test_validate_raw_cli_failure_is_nonzero(
    monkeypatch,
    capsys,
):
    report = RawValidationReport(
        checks=(
            ValidationCheck(
                "check_one",
                False,
                "broken",
            ),
        )
    )

    monkeypatch.setattr(
        validate_raw_cli,
        "get_connection",
        lambda: FakeConnectionContext(),
    )

    validator = MagicMock()
    validator.validate.return_value = report

    monkeypatch.setattr(
        validate_raw_cli,
        "RawValidator",
        MagicMock(
            return_value=validator
        ),
    )

    with pytest.raises(
        SystemExit
    ) as exc:
        validate_raw_cli.main()

    assert exc.value.code == 1

    output = capsys.readouterr().out

    assert "FAIL check_one" in output
    assert (
        "RAW VALIDATION FAILED"
        in output
    )
