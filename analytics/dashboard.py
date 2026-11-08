from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone

from accounts.models import AuditLog
from accounts.permissions import (
    ADMINISTRATOR,
    EMPLOYEE,
    HR_OFFICER,
    MANAGER,
    has_permission,
    role_name,
    scope_queryset,
)
from employees.models import Employee
from leave.models import Attendance, LeaveRequest
from recruitment.models import JobVacancy

from .charts import absenteeism_chart, leave_chart
from .metrics import add_months, month_start, number
from .services import load_report, scoped_employees


def _stat(label, value, note="", tone=""):
    return {"label": label, "value": value, "note": note, "tone": tone}


def _dashboard_role(user):
    role = role_name(user)
    if role in (HR_OFFICER, MANAGER, EMPLOYEE, ADMINISTRATOR):
        return role
    if user.is_superuser:
        return HR_OFFICER
    return None


def _team(user, today):
    report = load_report(user, add_months(month_start(today), -5), today, today=today)
    employees = scoped_employees(user).exclude(employment_status=Employee.EmploymentStatus.INACTIVE)
    leave = scope_queryset(LeaveRequest.objects.all(), user)
    on_leave_today = (
        leave.filter(
            status=LeaveRequest.Status.APPROVED, start_date__lte=today, end_date__gte=today
        )
        .values("employee")
        .distinct()
        .count()
    )
    pending = leave.filter(status=LeaveRequest.Status.PENDING).count()
    this_month = report.months[-1]["bucket"]
    return report, employees, on_leave_today, pending, this_month


def _hr_context(user, today):
    report, employees, on_leave_today, pending, this_month = _team(user, today)
    open_vacancies = JobVacancy.objects.filter(status=JobVacancy.Status.OPEN).count()
    departments = (
        employees.values("department__department_name")
        .annotate(total=Count("id"))
        .order_by("department__department_name")
    )
    return {
        "stats": [
            _stat("Headcount", employees.count(), "Active, onboarding or on leave"),
            _stat("On leave today", on_leave_today, tone="green"),
            _stat("Pending leave requests", pending, tone="amber"),
            _stat("Open vacancies", open_vacancies, tone="grey"),
            _stat("Absenteeism this month", f"{this_month.absenteeism:.1f}%", tone="amber"),
        ],
        "leave_chart": leave_chart(report),
        "absenteeism_chart": absenteeism_chart(report),
        "departments": departments,
    }


def _manager_context(user, today):
    report, employees, on_leave_today, pending, this_month = _team(user, today)
    employee = getattr(user, "employee", None)
    headcount = employees.count()
    checked_in = (
        scope_queryset(Attendance.objects.filter(date=today), user)
        .exclude(check_in_time__isnull=True)
        .count()
    )
    department = employee.department.department_name if employee else "No department"
    return {
        "stats": [
            _stat("Team headcount", headcount, department),
            _stat("On leave today", on_leave_today, tone="green"),
            _stat("Awaiting your approval", pending, tone="amber"),
            _stat("Checked in today", f"{checked_in} of {headcount}", tone="grey"),
            _stat("Absenteeism this month", f"{this_month.absenteeism:.1f}%", tone="amber"),
        ],
        "leave_chart": leave_chart(report),
        "absenteeism_chart": absenteeism_chart(report),
    }


def _employee_context(user, today):
    employee = getattr(user, "employee", None)
    if employee is None:
        return {"stats": [], "no_employee": True}
    requests = LeaveRequest.objects.filter(employee=employee)
    taken = (
        requests.filter(status=LeaveRequest.Status.APPROVED, start_date__year=today.year)
        .values("leave_type")
        .annotate(days=Sum("days_requested"))
    )
    days_by_type = {row["leave_type"]: row["days"] for row in taken}
    month = load_report(user, month_start(today), today, today=today)
    checked_in = Attendance.objects.filter(
        employee=employee, date=today, check_in_time__isnull=False
    ).exists()
    return {
        "stats": [
            _stat(
                "Annual leave taken",
                number(float(days_by_type.get(LeaveRequest.LeaveType.ANNUAL.value, 0))),
                f"Days in {today.year}",
                "green",
            ),
            _stat(
                "Sick leave taken",
                number(float(days_by_type.get(LeaveRequest.LeaveType.SICK.value, 0))),
                f"Days in {today.year}",
                "amber",
            ),
            _stat(
                "Pending requests",
                requests.filter(status=LeaveRequest.Status.PENDING).count(),
                tone="amber",
            ),
            _stat("Days absent this month", month.totals.absent, tone="grey"),
            _stat("Checked in today", "Yes" if checked_in else "No"),
        ],
        "recent_requests": requests.order_by("-date_submitted", "-id")[:5],
    }


def _admin_context(user, today):
    now = timezone.now()
    users = get_user_model().objects.all()
    entries = AuditLog.objects.all()
    context = {
        "stats": [
            _stat("Active users", users.filter(is_active=True).count()),
            _stat(
                "Locked accounts",
                users.filter(locked_until__gt=now).count(),
                tone="amber",
            ),
            _stat(
                "Failed logins",
                entries.filter(
                    action=AuditLog.Action.LOGIN_FAILED,
                    created_at__gte=now - timedelta(days=7),
                ).count(),
                "Last 7 days",
                "amber",
            ),
            _stat(
                "Audit entries today",
                entries.filter(created_at__date=today).count(),
                tone="grey",
            ),
        ],
    }
    if has_permission(user, "audit.view"):
        context["recent_audit"] = entries.select_related("user")[:5]
    return context


BUILDERS = {
    HR_OFFICER: _hr_context,
    MANAGER: _manager_context,
    EMPLOYEE: _employee_context,
    ADMINISTRATOR: _admin_context,
}


def dashboard_context(request):
    user = request.user
    role = _dashboard_role(user)
    if role is None:
        return {}
    today = timezone.localdate()
    context = BUILDERS[role](user, today)
    context["dashboard_role"] = role
    context["can_view_reports"] = has_permission(user, "reports.view")
    return context
