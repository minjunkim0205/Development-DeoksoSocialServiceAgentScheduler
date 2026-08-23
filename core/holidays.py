from __future__ import annotations

from datetime import date


WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def get_month_off_dates(year: int, month: int) -> set[date]:
    """Return weekend + Korean public holiday dates for a month.

    The optional `holidays` package handles Korean legal holidays, including
    substitute holidays when the package version knows them. Without it, the
    app still works with weekends as the baseline.
    """
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    dates = {date(year, month, day) for day in range(1, last_day + 1)}
    off_dates = {work_date for work_date in dates if work_date.weekday() >= 5}

    try:
        import holidays
    except ImportError:
        return off_dates

    korean_holidays = holidays.country_holidays("KR", years=[year])
    off_dates.update(work_date for work_date in dates if work_date in korean_holidays)
    return off_dates


def weekday_label(work_date: date) -> str:
    return WEEKDAY_LABELS[work_date.weekday()]
