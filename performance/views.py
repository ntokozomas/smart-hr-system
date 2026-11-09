
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404

from accounts.permissions import require_permission, scope_queryset
from .models import PerformanceRecord
from .forms import PerformanceRecordForm


@require_permission(
    "performance.manage",
    "performance.view",
    "performance.view_own",
)
def home(request):
    """Display performance reviews according to the user's access scope."""
    performance_records = scope_queryset(
        PerformanceRecord.objects.select_related(
            "employee", "reviewed_by"
        ),
        request.user,
    )

    context = {
        "performance_records": performance_records,
    }

    return render(request, "performance/home.html", context)


@require_permission("performance.manage")
def create_review(request):
    """Create a performance review for an employee within the user's scope."""
    if request.method == "POST":
        form = PerformanceRecordForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            performance_record = form.save(commit=False)
            performance_record.reviewed_by = request.user
            performance_record.save()

            messages.success(
                request,
                "Performance review created successfully."
            )

            return redirect("performance:home")
    else:
        form = PerformanceRecordForm(user=request.user)

    context = {
        "form": form,
    }

    return render(request, "performance/create_review.html", context)


@require_permission("performance.manage")
def edit_review(request, pk):
    """Edit a performance review within the user's access scope."""
    performance_record = get_object_or_404(
        scope_queryset(
            PerformanceRecord.objects.select_related("employee"),
            request.user,
        ),
        pk=pk,
    )

    if request.method == "POST":
        form = PerformanceRecordForm(
            request.POST,
            instance=performance_record,
            user=request.user,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Performance review updated successfully."
            )

            return redirect("performance:home")
    else:
        form = PerformanceRecordForm(
            instance=performance_record,
            user=request.user,
        )

    context = {
        "form": form,
        "performance_record": performance_record,
    }

    return render(
        request,
        "performance/edit_review.html",
        context
    )


@require_permission("performance.manage")
def delete_review(request, pk):
    """Delete a performance review within the user's access scope."""
    performance_record = get_object_or_404(
        scope_queryset(
            PerformanceRecord.objects.select_related("employee"),
            request.user,
        ),
        pk=pk,
    )

    if request.method == "POST":
        performance_record.delete()

        messages.success(
            request,
            "Performance review deleted successfully."
        )

        return redirect("performance:home")

    context = {
        "performance_record": performance_record,
    }

    return render(
        request,
        "performance/delete_review.html",
        context
    )
