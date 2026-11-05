from datetime import date, timedelta

import holidays


def calculate_working_days(start_date: date, end_date: date) -> int:
    """Calculate working days excluding weekends and South African public holidays."""

    if end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    public_holidays = holidays.country_holidays(
        "ZA",
        years=range(start_date.year, end_date.year + 1),
        observed=True,
    )

    working_days = 0
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in public_holidays:
            working_days += 1

        current_date += timedelta(days=1)

    return working_days
