import calendar
from datetime import date, datetime, timedelta


def add_months(d: datetime, months: int) -> datetime:
    if (d.month + months) > 12:
        next_month = (d.month + months) % 12
        years = (d.month + months) // 12
        next_year = d.year + years
    else:
        next_month = d.month + months
        next_year = d.year
    proposed = d + timedelta(days=months*30)
    next_fdow, next_eom = calendar.monthrange(next_year, next_month)
    if proposed.month == next_month:
        # ended up in predicted month
        fdow, eom = calendar.monthrange(d.year, d.month)
        if d.day == eom:
            return datetime(proposed.year, proposed.month, next_eom)

        # occur on the same date
        fdow, eom = calendar.monthrange(proposed.year, proposed.month)
        if d.day > eom:
            return datetime(proposed.year, proposed.month, eom)
        return datetime(proposed.year, proposed.month, d.day)
    elif proposed.month == d.month:
        # ended up in the same month, meaning we're in the early part of 31-day month
        return datetime(next_year, next_month, d.day)
    else:
        # prediction overshoots
        return datetime(next_year, next_month, d.day)
