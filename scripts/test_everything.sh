#!/bin/bash

# ============================================================
# SMART HR SYSTEM - COMPLETE PROJECT VERIFICATION
# Branch: Juandre
# Purpose: Verify database, models, admin, migrations,
#          automated tests and code quality before Git push.
# ============================================================

set -u

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0

run_check() {
    local description="$1"
    shift

    echo ""
    echo "============================================================"
    echo "TEST: $description"
    echo "============================================================"

    if "$@"; then
        echo "RESULT: PASS"
        PASS=$((PASS + 1))
    else
        echo "RESULT: FAIL"
        FAIL=$((FAIL + 1))
    fi
}

# 1. Verify the correct Git branch.
echo ""
echo "SMART HR SYSTEM TEST SUITE"
echo "Project: $PROJECT_ROOT"

BRANCH="$(git branch --show-current)"
echo "Current branch: $BRANCH"

if [ "$BRANCH" != "Juandre" ]; then
    echo "ERROR: You are not on the Juandre branch."
    exit 1
fi

# 2. Verify Python and Django.
run_check "Django system checks" \
    python manage.py check

# 3. Verify PostgreSQL connectivity.
run_check "PostgreSQL database connectivity" \
    python manage.py shell -c "
from django.db import connection
connection.ensure_connection()
print('Database vendor:', connection.vendor)
print('Database:', connection.settings_dict['NAME'])
assert connection.vendor == 'postgresql'
"

# 4. Verify migration consistency.
run_check "No unapplied migrations" \
    python manage.py migrate --check

run_check "No missing model migrations" \
    python manage.py makemigrations --check --dry-run

# 5. Verify all 17 required models and admin registrations.
run_check "All 17 models and admin registrations" \
    python manage.py shell -c "
from django.apps import apps
from django.contrib import admin

required = {
    'accounts': [
        'Role', 'Permission', 'User',
        'RolePermission', 'UserPermission'
    ],
    'employees': [
        'Department', 'JobPosition', 'Employee'
    ],
    'leave': [
        'LeaveRequest', 'Attendance'
    ],
    'lifecycle': [
        'Onboarding', 'OnboardingTask', 'EmployeeExit'
    ],
    'performance': [
        'PerformanceRecord'
    ],
    'recruitment': [
        'JobVacancy', 'Applicant', 'Application'
    ],
}

total = 0

for app_label, model_names in required.items():
    for model_name in model_names:
        model = apps.get_model(app_label, model_name)

        assert model is not None, (
            f'Missing model: {app_label}.{model_name}'
        )

        assert model in admin.site._registry, (
            f'Not registered in admin: {model_name}'
        )

        print(f'PASS: {app_label}.{model_name}')
        total += 1

print(f'\\nVerified models: {total}/17')
assert total == 17
"

# 6. Verify the four default roles.
run_check "Default role records" \
    python manage.py shell -c "
from accounts.models import Role

expected = {
    'Administrator',
    'HR Officer',
    'Manager',
    'Employee',
}

actual = set(Role.objects.values_list('role_name', flat=True))

for role in sorted(expected):
    assert role in actual, f'Missing role: {role}'
    print('PASS:', role)

print('All four default roles exist.')
"

# 7. Verify the administrator account.
run_check "Administrator superuser account" \
    python manage.py shell -c "
from accounts.models import User

user = User.objects.get(username='admin')

assert user.is_superuser
assert user.is_staff
assert user.is_active
assert user.role.role_name == 'Administrator'

print('Username:', user.username)
print('Active:', user.is_active)
print('Staff:', user.is_staff)
print('Role:', user.role.role_name)
"

# 8. Inspect database constraints and indexes.
run_check "Database constraint inspection" \
    python manage.py shell -c "
from django.apps import apps
from django.db import connection

required = [
    ('accounts', 'Role'),
    ('accounts', 'Permission'),
    ('accounts', 'RolePermission'),
    ('accounts', 'UserPermission'),
    ('accounts', 'User'),
    ('employees', 'Department'),
    ('employees', 'JobPosition'),
    ('employees', 'Employee'),
    ('leave', 'LeaveRequest'),
    ('leave', 'Attendance'),
    ('lifecycle', 'Onboarding'),
    ('lifecycle', 'OnboardingTask'),
    ('lifecycle', 'EmployeeExit'),
    ('performance', 'PerformanceRecord'),
    ('recruitment', 'JobVacancy'),
    ('recruitment', 'Applicant'),
    ('recruitment', 'Application'),
]

total_constraints = 0

with connection.cursor() as cursor:
    for app_label, model_name in required:
        model = apps.get_model(app_label, model_name)
        table = model._meta.db_table
        constraints = connection.introspection.get_constraints(
            cursor, table
        )

        model_constraints = sum(
            1 for item in constraints.values()
            if item.get('check') or item.get('unique') or item.get('primary_key')
        )

        total_constraints += model_constraints

        print(
            f'{model_name}: '
            f'{model_constraints} database constraints/indexes'
        )

print('\\nTotal inspected:', total_constraints)
assert total_constraints > 0
"

# 9. Run the automated Django test suite.
run_check "Django automated tests" \
    python manage.py test --verbosity=2

# 10. Run Ruff code-quality checks.
run_check "Ruff code-quality checks" \
    ruff check accounts employees leave lifecycle performance recruitment config

# 11. Check whitespace and Git patch formatting.
run_check "Git whitespace verification" \
    git diff --check

# 12. Final report.
echo ""
echo "============================================================"
echo "SMART HR SYSTEM - FINAL TEST REPORT"
echo "============================================================"

echo "Branch: $BRANCH"
echo "Passed checks: $PASS"
echo "Failed checks: $FAIL"

if [ "$FAIL" -eq 0 ]; then
    echo ""
    echo "ALL VERIFICATION STAGES PASSED."
    echo "Review the test output before committing and pushing."
    exit 0
else
    echo ""
    echo "SOME VERIFICATION STAGES FAILED."
    echo "Fix the reported issues before pushing."
    exit 1
fi
