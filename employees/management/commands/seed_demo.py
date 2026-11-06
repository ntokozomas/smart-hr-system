"""T6: load demo data for testing and the presentation.

    python manage.py seed_demo           add the demo data (safe to run again)
    python manage.py seed_demo --reset   remove the demo data first, then load it again

The data matches the case-study SME and the wireframes in Design 4.7.5: 45 staff in four
departments, a user for every role, leave (including a department clash next week),
two weeks of attendance, open vacancies with applicants, onboarding, an exit and
performance reviews. Every name is fictional. All demo users share DEMO_PASSWORD.

Dates are worked out from today, so "next week's leave" is always next week.
"""

import random
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from employees.models import Department, Employee, JobPosition
from leave.models import Attendance, LeaveRequest
from leave.utils import calculate_working_days
from lifecycle.models import EmployeeExit, Onboarding, OnboardingTask
from performance.models import PerformanceRecord
from recruitment.models import Applicant, Application, JobVacancy

DEMO_PASSWORD = "SmartHr2026"
STAFF_DOMAIN = "smarthr.demo"          # demo employees and users: name@smarthr.demo
APPLICANT_DOMAIN = "applicant.demo"    # demo applicants: name@applicant.demo

DEPARTMENTS = {
    "Warehouse & Operations": "Receiving, storing and dispatching stock.",
    "Sales": "Customer accounts and sales targets.",
    "Finance & Admin": "Finance, administration and HR.",
    "Management": "Company leadership.",
}

# The people the wireframes and demo script refer to by name:
# (first, last, department, position, role or None, username)
KEY_PEOPLE = [
    ("Johan", "van Wyk", "Warehouse & Operations", "Warehouse Manager", "Manager", "johan"),
    ("Kagiso", "Molefe", "Sales", "Sales Manager", "Manager", "kagiso"),
    ("Priya", "Pillay", "Finance & Admin", "Finance Manager", "Manager", "priya"),
    ("Nomsa", "Mahlangu", "Management", "General Manager", "Manager", "nomsa"),
    ("Thandi", "Nkosi", "Finance & Admin", "HR Officer", "HR Officer", "thandi"),
    ("Sipho", "Dlamini", "Warehouse & Operations", "Stock Controller", "Employee", "sipho"),
    ("Lerato", "Mokoena", "Sales", "Sales Representative", "Employee", "lerato"),
    ("Ayanda", "Khumalo", "Warehouse & Operations", "Forklift Operator", None, None),
    ("Pieter", "Botha", "Warehouse & Operations", "Dispatch Clerk", None, None),
    ("Musa", "Zwane", "Warehouse & Operations", "Warehouse Assistant", None, None),
]

# Everyone else, to reach 22 / 11 / 8 / 4 staff (45 in total) as in Figure 4.7.1.
OTHER_POSITIONS = {
    "Warehouse & Operations": ["Stock Controller", "Forklift Operator", "Warehouse Assistant",
                               "Dispatch Clerk"],
    "Sales": ["Sales Representative"],
    "Finance & Admin": ["Accountant", "Admin Clerk"],
    "Management": ["Operations Manager", "Marketing Manager"],
}
HEADCOUNT = {"Warehouse & Operations": 22, "Sales": 11, "Finance & Admin": 8, "Management": 4}

FIRST_NAMES = [
    "Andile", "Bongani", "Busisiwe", "Chantal", "Dineo", "Elias", "Fatima", "Gugu", "Hendrik",
    "Itumeleng", "Jabu", "Karabo", "Lindiwe", "Mpho", "Nandi", "Olwethu", "Palesa", "Refentse",
    "Sanele", "Tebogo", "Thabiso", "Unathi", "Vusi", "Wandile", "Xolani", "Yolanda", "Zodwa",
    "Ruan", "Megan", "Tshepo", "Kayla", "Sibusiso", "Anele", "Liam", "Naledi",
]
LAST_NAMES = [
    "Mabaso", "Ngcobo", "Petersen", "Radebe", "Sithebe", "Tshabalala", "Venter", "Zulu",
    "Hendricks", "Mthembu", "Naidoo", "Coetzee", "Maseko", "Ndlovu", "Ramaphosa", "Shabangu",
    "Smit", "Cele", "Daniels", "Govender", "Khoza", "Le Roux", "Mkhize", "Nel",
]

ONBOARDING_TASKS = [
    ("Sign employment contract", True),
    ("Set up system account", True),
    ("Health and safety induction", True),
    ("Issue PPE and access card", False),
    ("Meet the team and buddy", False),
]

# Applicants from Figure 4.7.4: (first, last, vacancy, status, match score)
APPLICANTS = [
    ("Naledi", "Mthembu", "Warehouse Supervisor", "Received", 82),
    ("Kyle", "Adams", "Warehouse Supervisor", "Received", 64),
    ("Zanele", "Ndlovu", "Warehouse Supervisor", "Received", 47),
    ("Michael", "Peters", "Warehouse Supervisor", "Screening", 76),
    ("Bongani", "Zulu", "Warehouse Supervisor", "Screening", 71),
    ("Priya", "Naidoo", "Warehouse Supervisor", "Interview", 88),
    ("Thabo", "Sithole", "Warehouse Supervisor", "Interview", 79),
    ("Grace", "Molefe", "Warehouse Supervisor", "Offer", 91),
    ("Dean", "Smith", "Warehouse Supervisor", "Rejected", 33),
    ("Aisha", "Patel", "Sales Representative", "Received", 69),
    ("Sizwe", "Gumede", "Sales Representative", "Screening", 74),
    ("Carmen", "Jacobs", "Sales Representative", "Interview", 85),
    ("Lwazi", "Mnguni", "Sales Representative", "Received", 58),
    ("Bianca", "Fourie", "Junior Accountant", "Hired", 90),
]


def demo_email(first, last, domain=STAFF_DOMAIN):
    return f"{first}.{last}".lower().replace(" ", "") + f"@{domain}"


def simple_pdf(text):
    """A tiny valid one-page PDF with one line of text, used as a demo CV."""
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


class Command(BaseCommand):
    help = "Load demo data (T6). Safe to run more than once; use --reset to start clean."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove demo data first.")
        parser.add_argument(
            "--force", action="store_true", help="Allow running when DEBUG is off."
        )
        parser.add_argument(
            "--no-cv-files", action="store_true", help="Do not write demo CV files to disk."
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "DEBUG is off, so this looks like a live system. Use --force if you are sure."
            )

        self.rng = random.Random(2026)  # same "random" data every time
        self.today = timezone.localdate()
        self.write_cvs = not options["no_cv_files"]

        with transaction.atomic():
            if options["reset"]:
                self.reset()
            if Employee.objects.filter(email__endswith=f"@{STAFF_DOMAIN}").exists():
                self.stdout.write("Demo data is already loaded. Use --reset to reload it.")
            else:
                self.load()
        self.print_logins()

    # ------------------------------------------------------------------ reset
    def reset(self):
        staff = Employee.objects.filter(email__endswith=f"@{STAFF_DOMAIN}")
        LeaveRequest.objects.filter(employee__in=staff).delete()
        Attendance.objects.filter(employee__in=staff).delete()
        PerformanceRecord.objects.filter(employee__in=staff).delete()
        OnboardingTask.objects.filter(onboarding__employee__in=staff).delete()
        Onboarding.objects.filter(employee__in=staff).delete()
        EmployeeExit.objects.filter(employee__in=staff).delete()
        Application.objects.filter(applicant__email__endswith=f"@{APPLICANT_DOMAIN}").delete()
        Applicant.objects.filter(email__endswith=f"@{APPLICANT_DOMAIN}").delete()
        JobVacancy.objects.filter(title__in=self.vacancy_titles()).exclude(
            pk__in=Application.objects.values("vacancy")
        ).delete()
        User.objects.filter(email__endswith=f"@{STAFF_DOMAIN}").delete()
        staff.update(manager=None)
        staff.delete()
        self.stdout.write("Removed the old demo data.")

    # ------------------------------------------------------------------- load
    def load(self):
        self.departments = {
            name: Department.objects.get_or_create(
                department_name=name, defaults={"description": text}
            )[0]
            for name, text in DEPARTMENTS.items()
        }
        self.positions = {}
        self.users = {}

        self.create_people()
        self.create_leave()
        self.create_attendance()
        self.create_lifecycle()
        self.create_performance()
        self.create_recruitment()

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {Employee.objects.filter(email__endswith=f'@{STAFF_DOMAIN}').count()} "
            f"employees, {LeaveRequest.objects.count()} leave requests, "
            f"{Attendance.objects.count()} attendance records and "
            f"{Application.objects.count()} applications."
        ))

    def position(self, title):
        if title not in self.positions:
            self.positions[title] = JobPosition.objects.get_or_create(position_title=title)[0]
        return self.positions[title]

    def new_employee(self, first, last, department, title, **extra):
        defaults = dict(
            first_name=first,
            last_name=last,
            email=demo_email(first, last),
            phone_number=f"08{self.rng.randint(10000000, 99999999)}",
            address=f"{self.rng.randint(1, 200)} {self.rng.choice(['Oak', 'Main', 'Church', 'Market'])} "
            f"Street, {self.rng.choice(['Pretoria', 'Johannesburg', 'Centurion', 'Midrand'])}",
            date_of_birth=date(self.rng.randint(1972, 2002), self.rng.randint(1, 12), self.rng.randint(1, 28)),
            date_joined=date(self.rng.randint(2018, 2025), self.rng.randint(1, 12), self.rng.randint(1, 28)),
            department=self.departments[department],
            position=self.position(title),
        )
        defaults.update(extra)
        return Employee.objects.create(**defaults)

    def create_people(self):
        self.key = {}
        for first, last, dept, title, role, username in KEY_PEOPLE:
            extra = {}
            if first == "Musa":  # new starter, still onboarding
                extra = {"date_joined": self.today - timedelta(days=10), "employment_status": "Onboarding"}
            employee = self.new_employee(first, last, dept, title, **extra)
            self.key[first] = employee
            if role:
                self.users[username] = User.objects.create_user(
                    username=username,
                    email=employee.email,
                    password=DEMO_PASSWORD,
                    first_name=first,
                    last_name=last,
                    role=Role.objects.get(role_name=role),
                    employee=employee,
                )

        self.users["sysadmin"] = User.objects.create_user(
            username="sysadmin",
            email=f"sysadmin@{STAFF_DOMAIN}",
            password=DEMO_PASSWORD,
            first_name="System",
            last_name="Administrator",
            role=Role.objects.get(role_name="Administrator"),
        )

        managers = {
            "Warehouse & Operations": self.key["Johan"],
            "Sales": self.key["Kagiso"],
            "Finance & Admin": self.key["Priya"],
            "Management": self.key["Nomsa"],
        }
        self.manager_users = {
            dept: User.objects.get(employee=emp) for dept, emp in managers.items()
        }

        used = {(p[0], p[1]) for p in KEY_PEOPLE}
        for dept, total in HEADCOUNT.items():
            current = Employee.objects.filter(department=self.departments[dept]).count()
            for _ in range(total - current):
                while True:
                    name = (self.rng.choice(FIRST_NAMES), self.rng.choice(LAST_NAMES))
                    if name not in used:
                        used.add(name)
                        break
                self.new_employee(*name, dept, self.rng.choice(OTHER_POSITIONS[dept]))

        for dept, manager in managers.items():
            Employee.objects.filter(department=self.departments[dept]).exclude(
                pk=manager.pk
            ).update(manager=manager)
        Employee.objects.filter(pk__in=[m.pk for m in managers.values()]).exclude(
            pk=self.key["Nomsa"].pk
        ).update(manager=self.key["Nomsa"])

        # One employee who left last month (FR-29). Not counted in the 45.
        leaver = self.new_employee(
            "Brian", "Naidoo", "Sales", "Sales Representative",
            employment_status="Inactive", date_joined=date(2021, 3, 1),
        )
        self.leaver = leaver

    # ------------------------------------------------------------------ leave
    def leave(self, employee, kind, start, end, status, reason=""):
        days = calculate_working_days(start, end) or 1
        decided = status in ("Approved", "Rejected")
        approver = self.manager_users.get(employee.department.department_name)
        if approver and approver.employee_id == employee.pk:  # a manager's own leave
            approver = self.users["thandi"]
        return LeaveRequest.objects.create(
            employee=employee,
            leave_type=kind,
            start_date=start,
            end_date=end,
            days_requested=days,
            reason=reason or None,
            status=status,
            approved_by=approver if decided else None,
            decided_at=timezone.now() if decided else None,
        )

    def create_leave(self):
        staff = list(
            Employee.objects.filter(email__endswith=f"@{STAFF_DOMAIN}", employment_status="Active")
        )

        # Past approved leave for the trend chart (FR-36): roughly the last five months.
        for months_back in range(1, 6):
            month_start = (self.today.replace(day=1) - timedelta(days=30 * months_back)).replace(day=1)
            for _ in range(self.rng.randint(6, 10)):
                employee = self.rng.choice(staff)
                start = month_start + timedelta(days=self.rng.randint(0, 24))
                end = start + timedelta(days=self.rng.randint(0, 4))
                kind = self.rng.choice(["Annual", "Annual", "Sick", "Family"])
                self.leave(employee, kind, start, end, "Approved")

        # Next week: Sipho's request clashes with two approved colleagues (FR-18, Figure 4.7.3).
        monday = self.today + timedelta(days=7 - self.today.weekday())
        k = self.key
        self.leave(k["Ayanda"], "Annual", monday + timedelta(days=1), monday + timedelta(days=3), "Approved")
        self.leave(k["Pieter"], "Annual", monday + timedelta(days=2), monday + timedelta(days=4), "Approved")
        self.leave(k["Sipho"], "Annual", monday, monday + timedelta(days=4), "Pending", "Family holiday")
        self.leave(k["Lerato"], "Family", monday + timedelta(days=7), monday + timedelta(days=7),
                   "Pending", "Child's school event")

        # Three people on leave today (dashboard card).
        on_leave_today = [p for p in staff if p not in k.values()][:3]
        for person, kind in zip(on_leave_today, ["Annual", "Annual", "Sick"]):
            self.leave(person, kind, self.today - timedelta(days=1), self.today + timedelta(days=1), "Approved")
        self.on_leave_today = set(p.pk for p in on_leave_today)

        # A rejected request, so every status appears.
        self.leave(k["Lerato"], "Annual", self.today - timedelta(days=40), self.today - timedelta(days=38),
                   "Rejected", "Month-end busy period")

    # ------------------------------------------------------------- attendance
    def create_attendance(self):
        staff = Employee.objects.filter(email__endswith=f"@{STAFF_DOMAIN}").exclude(
            employment_status="Inactive"
        )
        days, day = [], self.today
        while len(days) < 10:
            day -= timedelta(days=1)
            if day.weekday() < 5:
                days.append(day)

        records = []
        for employee in staff:
            approved = list(
                LeaveRequest.objects.filter(employee=employee, status="Approved")
                .values_list("start_date", "end_date")
            )
            for day in days + [self.today]:
                if day < employee.date_joined:
                    continue
                if any(start <= day <= end for start, end in approved):
                    records.append(Attendance(employee=employee, date=day, status="On Leave"))
                    continue
                roll = self.rng.random()
                if roll < 0.03:
                    records.append(Attendance(employee=employee, date=day, status="Absent"))
                    continue
                minutes = self.rng.randint(-20, 10) if roll > 0.08 else self.rng.randint(20, 50)
                check_in = (datetime.combine(day, time(8, 0)) + timedelta(minutes=minutes)).time()
                check_out = None
                if day != self.today:
                    check_out = time(self.rng.randint(16, 17), self.rng.randint(0, 59))
                records.append(Attendance(
                    employee=employee, date=day, check_in_time=check_in,
                    check_out_time=check_out, status="Late" if minutes > 15 else "Present",
                ))
        Attendance.objects.bulk_create(records)

    # -------------------------------------------------- onboarding and exits
    def create_lifecycle(self):
        musa = self.key["Musa"]
        onboarding = Onboarding.objects.create(
            employee=musa, start_date=musa.date_joined, status="In Progress",
            notes="Buddy: Sipho Dlamini.",
        )
        for name, done in ONBOARDING_TASKS:
            OnboardingTask.objects.create(
                onboarding=onboarding, task_name=name,
                status="Completed" if done else "Pending",
                completed_date=musa.date_joined + timedelta(days=2) if done else None,
            )
        EmployeeExit.objects.create(
            employee=self.leaver, exit_type="Resignation",
            exit_date=self.today - timedelta(days=25),
            reason="Moved to another city.",
            exit_procedures="Return laptop and access card; final pay; exit interview.",
            procedures_completed=True,
        )

    # ------------------------------------------------------------ performance
    def create_performance(self):
        reviewed = Employee.objects.filter(
            email__endswith=f"@{STAFF_DOMAIN}",
            department__department_name__in=["Warehouse & Operations", "Sales"],
            employment_status="Active",
        ).exclude(pk__in=[self.key["Johan"].pk, self.key["Kagiso"].pk])[:12]
        for employee in reviewed:
            reviewer = self.manager_users[employee.department.department_name]
            for period, review_day in (("2026 Q2", date(2026, 7, 10)), ("2026 Q3", date(2026, 10, 9))):
                PerformanceRecord.objects.create(
                    employee=employee, reviewed_by=reviewer, review_period=period,
                    review_date=review_day,
                    goals="Meet monthly targets; complete safety refresher.",
                    rating=self.rng.choice([2, 3, 3, 4, 4, 4, 5]),
                    comments="Reliable and works well with the team.",
                )

    # ------------------------------------------------------------ recruitment
    def vacancy_titles(self):
        return ["Warehouse Supervisor", "Sales Representative", "Junior Accountant"]

    def create_recruitment(self):
        specs = {
            "Warehouse Supervisor": ("Warehouse & Operations", "Open", 14, 9,
                                     "Lead the warehouse team on day shift.",
                                     "Matric; 3+ years warehouse experience; forklift licence."),
            "Sales Representative": ("Sales", "Open", 7, 21,
                                     "Grow and look after customer accounts in Gauteng.",
                                     "Matric; driver's licence; 1+ year sales experience."),
            "Junior Accountant": ("Finance & Admin", "Closed", 60, -20,
                                  "Support month-end and creditors.",
                                  "BCom Accounting or studying towards it."),
        }
        vacancies = {}
        for title, (dept, status, posted_ago, closes_in, description, requirements) in specs.items():
            vacancies[title] = JobVacancy.objects.create(
                title=title, department=self.departments[dept],
                position=self.position(title), description=description,
                requirements=requirements, status=status,
                date_posted=self.today - timedelta(days=posted_ago),
                closing_date=self.today + timedelta(days=closes_in),
            )

        storage = None
        if self.write_cvs:
            from recruitment.views import cv_storage as storage

        for first, last, title, status, score in APPLICANTS:
            email = demo_email(first, last, APPLICANT_DOMAIN)
            cv_path = f"private/recruitment/cvs/demo-{first}-{last}.pdf".lower()
            if storage is not None and not storage.exists(cv_path):
                cv_path = storage.save(cv_path, ContentFile(simple_pdf(f"CV - {first} {last}")))
            applicant = Applicant.objects.create(
                first_name=first, last_name=last, email=email,
                phone_number=f"07{self.rng.randint(10000000, 99999999)}",
                cv_path=cv_path, consent_given=True, consent_date=timezone.now(),
            )
            Application.objects.create(
                vacancy=vacancies[title], applicant=applicant, status=status,
                match_score=score,
                cover_letter=f"I would like to apply for the {title} position.",
            )

    # ---------------------------------------------------------------- summary
    def print_logins(self):
        self.stdout.write("")
        self.stdout.write(f"Demo logins (password for all: {DEMO_PASSWORD})")
        for username, role in (
            ("sysadmin", "Administrator"), ("thandi", "HR Officer"),
            ("johan", "Manager, Warehouse & Operations"), ("kagiso", "Manager, Sales"),
            ("sipho", "Employee, Warehouse"), ("lerato", "Employee, Sales"),
        ):
            self.stdout.write(f"  {username:<10} {role}")
