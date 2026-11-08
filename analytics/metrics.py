from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import holidays

LEAVE_TYPES = ("Annual", "Sick", "Family")
PRESENT_STATUSES = {"Present", "Late", "On Leave"}


def month_start(day):
    return day.replace(day=1)


def next_month(day):
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def add_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def months_between(start, end):
    months = []
    current = month_start(start)
    while current <= end:
        months.append(current)
        current = next_month(current)
    return months


def working_dates(start, end):
    if end < start:
        return []
    public_holidays = holidays.country_holidays(
        "ZA", years=range(start.year, end.year + 1), observed=True
    )
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in public_holidays:
            days.append(current)
        current += timedelta(days=1)
    return days


def rate(part, whole):
    if not whole:
        return 0.0
    return round(part * 100 / whole, 1)


@dataclass
class EmployeeRow:
    id: int
    department: str
    date_joined: date
    status: str
    exit_date: date | None = None


@dataclass
class Bucket:
    leave: dict = field(default_factory=lambda: {name: 0 for name in LEAVE_TYPES})
    expected: int = 0
    absent: int = 0
    late: int = 0
    headcount: int = 0

    @property
    def leave_total(self):
        return sum(self.leave.values())

    @property
    def absenteeism(self):
        return rate(self.absent, self.expected)


@dataclass
class Report:
    start: date
    end: date
    months: list
    departments: list
    totals: Bucket


def _is_current(employee, day):
    if employee.date_joined > day:
        return False
    if employee.exit_date is not None:
        return employee.exit_date >= day
    return employee.status != "Inactive"


def build_report(start, end, today, employees, leaves, attendance, tracking_start=None):
    in_range = working_dates(start, end)
    in_range_set = set(in_range)
    absence_end = min(end, today)
    if tracking_start is None:
        past_days = []
    else:
        past_days = [day for day in in_range if tracking_start <= day <= absence_end]

    by_id = {employee.id: employee for employee in employees}
    months = {month: Bucket() for month in months_between(start, end)}
    departments = defaultdict(Bucket)
    totals = Bucket()

    leave_days = defaultdict(dict)
    for employee_id, leave_type, leave_start, leave_end in leaves:
        if employee_id not in by_id:
            continue
        day = max(leave_start, start)
        last = min(leave_end, end)
        while day <= last:
            if day in in_range_set and day not in leave_days[employee_id]:
                leave_days[employee_id][day] = leave_type
            day += timedelta(days=1)

    for employee_id, days in leave_days.items():
        department = departments[by_id[employee_id].department]
        for day, leave_type in days.items():
            for bucket in (months[month_start(day)], department, totals):
                bucket.leave[leave_type] = bucket.leave.get(leave_type, 0) + 1

    attended = defaultdict(set)
    for employee_id, day, status in attendance:
        if employee_id not in by_id:
            continue
        if status in PRESENT_STATUSES:
            attended[employee_id].add(day)
        if status == "Late" and day in in_range_set:
            department = departments[by_id[employee_id].department]
            for bucket in (months[month_start(day)], department, totals):
                bucket.late += 1

    for employee in employees:
        department = departments[employee.department]
        if _is_current(employee, absence_end):
            department.headcount += 1
            totals.headcount += 1
        for day in past_days:
            if not _is_current(employee, day):
                continue
            absent = day not in attended[employee.id] and day not in leave_days[employee.id]
            for bucket in (months[month_start(day)], department, totals):
                bucket.expected += 1
                if absent:
                    bucket.absent += 1

    month_rows = [{"month": month, "bucket": bucket} for month, bucket in months.items()]
    department_rows = [
        {"department": name, "bucket": departments[name]} for name in sorted(departments)
    ]
    return Report(start, end, month_rows, department_rows, totals)


def number(value):
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.1f}"
    return str(int(value))


def absenteeism_text(bucket):
    if not bucket.expected:
        return "-"
    return f"{bucket.absenteeism:.1f}"


def report_tables(report):
    monthly_headers = [
        "Month",
        "Annual",
        "Sick",
        "Family",
        "Leave days",
        "Expected days",
        "Days absent",
        "Late arrivals",
        "Absenteeism %",
    ]

    def monthly_row(label, bucket):
        return [
            label,
            *(number(bucket.leave[name]) for name in LEAVE_TYPES),
            number(bucket.leave_total),
            number(bucket.expected),
            number(bucket.absent),
            number(bucket.late),
            absenteeism_text(bucket),
        ]

    monthly_rows = [
        monthly_row(row["month"].strftime("%b %Y"), row["bucket"]) for row in report.months
    ]
    monthly_rows.append(monthly_row("Total", report.totals))

    department_headers = [
        "Department",
        "Headcount",
        "Leave days",
        "Expected days",
        "Days absent",
        "Absenteeism %",
    ]
    department_rows = [
        [
            row["department"],
            number(row["bucket"].headcount),
            number(row["bucket"].leave_total),
            number(row["bucket"].expected),
            number(row["bucket"].absent),
            absenteeism_text(row["bucket"]),
        ]
        for row in report.departments
    ]

    return [
        ("Leave and absenteeism by month", monthly_headers, monthly_rows),
        ("By department", department_headers, department_rows),
    ]
