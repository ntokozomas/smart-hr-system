
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from accounts.permissions import require_permission
from .models import PerformanceRecord
from .forms import PerformanceRecordForm


@require_permission("performance.manage")
def home(request):
    """Display employee performance reviews."""
    performance_records = PerformanceRecord.objects.select_related(
        "employee", "reviewed_by"
    )

    context = {
        "performance_records": performance_records,
    }

    return render(request, "performance/home.html", context)


@require_permission("performance.manage")
def create_review(request):
    """Create a new employee performance review."""
    if request.method == "POST":
        form = PerformanceRecordForm(request.POST)

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
        form = PerformanceRecordForm()

    context = {
        "form": form,
    }

    return render(request, "performance/create_review.html", context)


@require_permission("performance.manage")
def edit_review(request, pk):
    """Edit an existing employee performance review."""
    performance_record = get_object_or_404(
        PerformanceRecord,
        pk=pk
    )

    if request.method == "POST":
        form = PerformanceRecordForm(
            request.POST,
            instance=performance_record
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
            instance=performance_record
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
    """Delete an existing employee performance review."""
    performance_record = get_object_or_404(
        PerformanceRecord,
        pk=pk
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
