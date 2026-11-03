"""Sidebar menu per role (Design 4.7.1, Table 4.7.1).

Each item is (label, URL name, permissions). The item shows when the user has any
of the permissions (None = everyone) AND the URL exists. So when you build your
module, give your main page the URL name listed here and it appears in the menu
automatically.
"""

MENU = [
    (
        "Main",
        [
            ("Dashboard", "dashboard", None),
            ("Employees", "employees:list", ("employees.view",)),
            ("My Profile", "employees:my_profile", ("profile.view_own",)),
        ],
    ),
    (
        "HR modules",
        [
            ("Leave", "leave:home", ("leave.apply", "leave.view", "leave.approve")),
            ("Attendance", "leave:attendance", ("attendance.record_own", "attendance.view")),
            ("Recruitment", "recruitment:home", ("recruitment.manage",)),
            ("Onboarding & Exit", "lifecycle:home", ("lifecycle.manage",)),
            (
                "Performance",
                "performance:home",
                ("performance.view", "performance.view_own", "performance.manage"),
            ),
        ],
    ),
    ("Insights", [("Reports", "analytics:reports", ("reports.view",))]),
    (
        "Administration",
        [
            ("Users & roles", "accounts:users", ("accounts.manage_users",)),
            ("Audit log", "accounts:audit_log", ("audit.view",)),
        ],
    ),
    ("Support", [("Help", "help", None)]),
]
