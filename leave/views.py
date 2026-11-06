
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import (
    has_permission,
    require_permission,
    scope_queryset,
)
from employees.models import Employee

from .forms import LeaveRequestForm
from .models import Attendance, LeaveRequest, LeaveBalance


@require_permission("leave.apply", "leave.view", "leave.approve")
def home(request):
    """Display leave requests and the logged-in employee's leave balances."""

    leave_requests = scope_queryset(
        LeaveRequest.objects.select_related(
            "employee",
            "employee__department",
            "approved_by",
        ),
        request.user,
    ).order_by("-date_submitted")

    employee = getattr(request.user, "employee", None)
    leave_balances = []

    if employee is not None:
        current_year = timezone.localdate().year

        leave_balances = LeaveBalance.objects.filter(
            employee=employee,
            year=current_year,
        ).order_by("leave_type")

    context = {
        "leave_requests": leave_requests,
        "leave_balances": leave_balances,
        "can_apply": has_permission(request.user, "leave.apply"),
        "can_approve": has_permission(request.user, "leave.approve"),
    }

    return render(request, "leave/home.html", context)


@require_permission("leave.apply")
def apply_leave(request):
    """Allow an employee to submit a leave application."""

    employee = getattr(request.user, "employee", None)

    if employee is None:
        raise PermissionDenied(
            "Your account is not linked to an employee record."
        )

    if request.method == "POST":
        form = LeaveRequestForm(
            request.POST,
            employee=employee,
        )

        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = employee
            leave_request.status = LeaveRequest.Status.PENDING

            overlapping_requests = LeaveRequest.objects.filter(
                employee=employee,
                status__in=[
                    LeaveRequest.Status.PENDING,
                    LeaveRequest.Status.APPROVED,
                ],
                start_date__lte=leave_request.end_date,
                end_date__gte=leave_request.start_date,
            )

            if overlapping_requests.exists():
                messages.warning(
                    request,
                    "You already have a pending or approved leave "
                    "request that overlaps with these dates. "
                    "Your new application will still be submitted "
                    "for review.",
                )

            leave_request.save()

            messages.success(
                request,
                "Your leave application was submitted successfully.",
            )

            return redirect("leave:home")

    else:
        form = LeaveRequestForm(employee=employee)

    return render(
        request,
        "leave/apply.html",
        {"form": form},
    )


@require_permission("leave.approve")
def review_leave(request, pk):
    """Allow authorised HR officers and managers to review leave requests."""

    pending_requests = scope_queryset(
        LeaveRequest.objects.select_related(
            "employee",
            "employee__department",
        ).filter(status=LeaveRequest.Status.PENDING),
        request.user,
    )

    leave_request = get_object_or_404(pending_requests, pk=pk)

    # Prevent managers or HR officers from reviewing their own leave requests.
    if leave_request.employee_id == request.user.employee_id:
        raise PermissionDenied(
            "You cannot review your own leave request."
        )

    department_conflicts = (
        LeaveRequest.objects.filter(
            employee__department_id=leave_request.employee.department_id,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=leave_request.end_date,
            end_date__gte=leave_request.start_date,
        )
        .exclude(pk=leave_request.pk)
        .exclude(employee_id=leave_request.employee_id)
        .select_related("employee")
    )

    if request.method == "POST":
        decision = request.POST.get("decision")

        if decision not in (
            LeaveRequest.Status.APPROVED,
            LeaveRequest.Status.REJECTED,
        ):
            messages.error(
                request,
                "Please select a valid decision.",
            )

        else:
            leave_request.status = decision
            leave_request.approved_by = request.user
            leave_request.decided_at = timezone.now()

            leave_request.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "decided_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                f"Leave application successfully {decision.lower()}.",
            )

            return redirect("leave:home")

    context = {
        "leave_request": leave_request,
        "department_conflicts": department_conflicts,
    }

    return render(
        request,
        "leave/review.html",
        context,
    )


@require_permission("attendance.record_own", "attendance.view")
def attendance(request):
    """Display attendance records and manage employee check-in and check-out."""

    employee = getattr(request.user, "employee", None)

    if request.method == "POST":
        if not has_permission(request.user, "attendance.record_own"):
            raise PermissionDenied

        if employee is None:
            raise PermissionDenied(
                "Your account is not linked to an employee record."
            )

        if employee.employment_status != Employee.EmploymentStatus.ACTIVE:
            messages.error(
                request,
                "Only active employees can record attendance.",
            )
            return redirect("leave:attendance")

        action = request.POST.get("action")
        today = timezone.localdate()
        current_time = timezone.localtime().time()

        if action == "check_in":
            record, created = Attendance.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={
                    "check_in_time": current_time,
                    "status": Attendance.Status.PRESENT,
                },
            )

            if created:
                messages.success(
                    request,
                    "Check-in recorded successfully.",
                )

            elif record.check_in_time is None:
                record.check_in_time = current_time
                record.status = Attendance.Status.PRESENT

                record.save(
                    update_fields=[
                        "check_in_time",
                        "status",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    "Check-in recorded successfully.",
                )

            else:
                messages.warning(
                    request,
                    "You have already checked in today.",
                )

        elif action == "check_out":
            record = Attendance.objects.filter(
                employee=employee,
                date=today,
            ).first()

            if record is None or record.check_in_time is None:
                messages.error(
                    request,
                    "You must check in before checking out.",
                )

            elif record.check_out_time is not None:
                messages.warning(
                    request,
                    "You have already checked out today.",
                )

            elif current_time <= record.check_in_time:
                messages.error(
                    request,
                    "Check-out time must be later than check-in time.",
                )

            else:
                record.check_out_time = current_time

                record.save(
                    update_fields=[
                        "check_out_time",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    "Check-out recorded successfully.",
                )

        else:
            messages.error(
                request,
                "Invalid attendance action.",
            )

        return redirect("leave:attendance")

    attendance_records = scope_queryset(
        Attendance.objects.select_related(
            "employee",
            "employee__department",
        ),
        request.user,
    ).order_by("-date")

    today_record = None

    if employee is not None:
        today_record = Attendance.objects.filter(
            employee=employee,
            date=timezone.localdate(),
        ).first()

    context = {
        "attendance_records": attendance_records,
        "today_record": today_record,
        "can_record": (
            has_permission(request.user, "attendance.record_own")
            and employee is not None
            and employee.employment_status == Employee.EmploymentStatus.ACTIVE
        ),
    }

    return render(
        request,
        "leave/attendance.html",
        context,
    )
