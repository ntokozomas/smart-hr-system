# Smart HR System (IT Project 700, Group 51)

Django 5.2 + PostgreSQL. Check the group's build reference before adding anything new.

## Setup (once)

1. Install Python 3.12 and PostgreSQL 16 or newer
   (Mac: Postgres.app; Windows: the EDB installer from postgresql.org).
2. Open psql (Windows: "SQL Shell (psql)") and run:
       CREATE USER smarthr WITH PASSWORD 'smarthr_dev';
       CREATE DATABASE smarthr OWNER smarthr;
       ALTER USER smarthr CREATEDB;   -- lets Django create its test database
3. Clone the repo and create a virtual environment:
   - Mac: python3.12 -m venv .venv && source .venv/bin/activate
   - Windows: py -3.12 -m venv .venv  then  .venv\Scripts\activate
4. pip install -r requirements.txt
5. Copy .env.example to .env, then put your own key in it. Generate one with:
       python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
6. python manage.py migrate
7. python manage.py createsuperuser
8. Load the demo data (45 staff, leave, attendance, applicants and more):
       python manage.py seed_demo
   It prints the demo logins (thandi = HR Officer, johan = Manager, sipho = Employee,
   sysadmin = Administrator; password SmartHr2026). To start fresh: seed_demo --reset

## Run

    python manage.py runserver

Then open http://127.0.0.1:8000/admin

## Rules

- Work on your own branch, e.g. feature/leave. Never push straight to main.
- Before pushing: ruff check . --fix && ruff format .  and  python manage.py test
- Open a pull request; one other person reviews before merging.
- Pull main every morning: git pull origin main
- Never commit .env

## Building your module (read before you start)

Everything below already exists in `main`. Use it instead of writing your own.

**1. URLs.** Create `yourapp/urls.py` with `app_name = "yourapp"`, add one line to
`config/urls.py` (e.g. `path("leave/", include("leave.urls"))`), and give your main page
the URL name from `accounts/menu.py`. It then appears in the sidebar automatically:

| Menu item | URL name | Owner |
| --- | --- | --- |
| Employees / My Profile / search | `employees:list`, `employees:my_profile`, `employees:search` | Angelique |
| Leave / Attendance | `leave:home`, `leave:attendance` | Refilwe |
| Recruitment | `recruitment:home` | Juandre |
| Onboarding & Exit / Performance | `lifecycle:home`, `performance:home` | Jonathan |
| Reports | `analytics:reports` | Graeme |

**2. Protect every view** (NFR-03). Every page already needs a login. Then check the permission:

    from accounts.permissions import require_permission, scope_queryset

    @require_permission("leave.approve")
    def approvals(request):
        pending = scope_queryset(LeaveRequest.objects.filter(status="Pending"), request.user)

`scope_queryset` gives HR Officers everything, Managers their own department and Employees
their own records. Pass `""` as the third argument when the queryset is `Employee` itself.
For class-based views use `RequirePermissionMixin` with `required_permissions = ("...",)`.
Permission codes are listed in `accounts/migrations/0008_seed_permissions.py`.
Public pages (the Careers pages) need `@login_not_required` from `django.contrib.auth.decorators`.

**3. Templates.** Extend the shared layout:

    {% extends "base.html" %}
    {% load ui %}
    {% block title %}Leave{% endblock %}
    {% block breadcrumbs %}<a href="{% url 'dashboard' %}">Dashboard</a> › Leave{% endblock %}
    {% block page_title %}Leave requests{% endblock %}
    {% block page_actions %}<a class="btn btn-primary" href="...">Apply for leave</a>{% endblock %}
    {% block content %} ... {% endblock %}

Ready-made pieces: `{% include "partials/form.html" with form=form submit_label="Submit" %}`,
`{% status_badge leave.status %}`, `{% include "partials/empty_state.html" with message="..." %}`,
`{% include "partials/pagination.html" %}`, and the CSS classes `card`, `data-table`
(inside `table-wrap`), `btn btn-primary / btn-success / btn-secondary / btn-danger`,
`stat-grid` + `stat-card`, `alert alert-warning`. Show messages with
`messages.success(request, "...")`. Public pages extend `base_public.html`.

**4. Audit log and notifications.** Logins, failed logins, lockouts, user and role changes,
employee changes and leave decisions are logged automatically. Log anything else that
matters, for example report exports, and notify people when something needs their attention:

    from accounts.audit import log_action
    from accounts.notifications import notify

    log_action("Export", "Exported the leave report as PDF")
    notify(employee.user_account, "Your onboarding task is due tomorrow.", link="/lifecycle/")
