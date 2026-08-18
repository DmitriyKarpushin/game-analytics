from src.storage.postgres import get_connection
from src.validation.raw import RawValidator


def main() -> None:
    with get_connection() as connection:
        report = RawValidator(
            connection
        ).validate()

    for check in report.checks:
        status = (
            "PASS"
            if check.passed
            else "FAIL"
        )

        print(
            f"{status} "
            f"{check.name} - "
            f"{check.details}"
        )

    passed_count = sum(
        check.passed
        for check in report.checks
    )

    total_count = len(
        report.checks
    )

    if not report.passed:
        print(
            f"RAW VALIDATION FAILED "
            f"({passed_count}/{total_count} passed)"
        )
        raise SystemExit(1)

    print(
        f"RAW VALIDATION PASSED "
        f"({passed_count}/{total_count})"
    )


if __name__ == "__main__":
    main()
