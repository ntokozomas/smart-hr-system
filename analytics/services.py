from django.db.models import Min
from django.utils import timezone

from accounts.permissions import scope_queryset
from employees.models import Employee
from leave.models import Attendance, LeaveRequest

from .metrics import EmployeeRow, build_report


def scoped_employees(user, department=None):
    employees = scope_queryset(Employee.objects.all(), user, "")
    if department is not None:
        employees = employees.filter(department=department)
    return employees


def load_report(user, start, end, department=None, leave_type="", today=None):
    today = today or timezone.localdate()
    employees = scoped_employees(user, department).values(
        "id",
        "department__department_name",
        "date_joined",
        "employment_status",
        "exit_record__exit_date",
    )
    rows = [
        EmployeeRow(
            id=employee["id"],
            department=employee["department__department_name"],
            date_joined=employee["date_joined"],
            status=employee["employment_status"],
            exit_date=employee["exit_record__exit_date"],
        )
        for employee in employees
    ]
    ids = [row.id for row in rows]

    leaves = scope_queryset(
        LeaveRequest.objects.filter(
            employee_id__in=ids,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=end,
            end_date__gte=start,
        ),
        user,
    )
    if leave_type:
        leaves = leaves.filter(leave_type=leave_type)

    attendance = scope_queryset(
        Attendance.objects.filter(employee_id__in=ids, date__range=(start, end)), user
    )

    tracking_start = Attendance.objects.aggregate(first=Min("date"))["first"]

    return build_report(
        start,
        end,
        today,
        rows,
        leaves.values_list("employee_id", "leave_type", "start_date", "end_date"),
        attendance.values_list("employee_id", "date", "status"),
        tracking_start=tracking_start,
    )
