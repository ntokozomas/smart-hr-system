from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError, transaction
from employees.models import Department, JobPosition
from recruitment.models import JobVacancy, Applicant, Application


class RecruitmentModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            department_name="Recruitment"
        )
        self.position = JobPosition.objects.create(
            position_title="Recruitment Specialist"
        )
        self.vacancy = JobVacancy.objects.create(
            department=self.department,
            position=self.position,
            title="Recruitment Specialist",
            description="Recruitment role",
            requirements="Relevant experience",
            date_posted=date.today(),
            closing_date=date.today() + timedelta(days=30),
        )
        self.applicant = Applicant.objects.create(
            first_name="Sam",
            last_name="Taylor",
            email="sam@example.com",
            cv_path="cvs/sam.pdf",
            consent_given=True,
            consent_date=__import__(
                "django.utils.timezone", fromlist=["now"]
            ).now(),
        )

    def test_job_vacancy_creation(self):
        self.assertEqual(self.vacancy.title, "Recruitment Specialist")

    def test_applicant_creation(self):
        self.assertEqual(self.applicant.email, "sam@example.com")

    def test_applicant_consent_must_be_given(self):
        from django.utils import timezone
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Applicant.objects.create(
                    first_name="No",
                    last_name="Consent",
                    email="no-consent@example.com",
                    cv_path="cvs/no-consent.pdf",
                    consent_given=False,
                    consent_date=timezone.now(),
                )

    def test_vacancy_closing_date_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JobVacancy.objects.create(
                    department=self.department,
                    position=self.position,
                    title="Invalid Vacancy",
                    description="Invalid",
                    requirements="Invalid",
                    date_posted=date.today(),
                    closing_date=date.today() - timedelta(days=1),
                )

    def test_application_creation(self):
        application = Application.objects.create(
            vacancy=self.vacancy,
            applicant=self.applicant,
            match_score=Decimal("85.0"),
        )
        self.assertEqual(application.match_score, Decimal("85.0"))

    def test_duplicate_application_rejected(self):
        Application.objects.create(
            vacancy=self.vacancy,
            applicant=self.applicant,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Application.objects.create(
                    vacancy=self.vacancy,
                    applicant=self.applicant,
                )

    def test_match_score_above_100_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Application.objects.create(
                    vacancy=self.vacancy,
                    applicant=self.applicant,
                    match_score=Decimal("101.0"),
                )

# COVERAGE_COMPLETION_TESTS
    def test_job_vacancy_string_representation(self):
        self.assertEqual(str(self.vacancy), "Recruitment Specialist")

    def test_applicant_string_representation(self):
        self.assertEqual(str(self.applicant), "Sam Taylor")

    def test_application_string_representation(self):
        application = Application.objects.create(
            vacancy=self.vacancy,
            applicant=self.applicant,
            match_score=Decimal("85.0"),
        )
        self.assertEqual(
            str(application),
            f"{self.applicant} - {self.vacancy}",
        )

# Relationship deletion tests for Section 4.5.11.
from django.db.models.deletion import ProtectedError


class RecruitmentRelationshipTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            department_name="Recruitment Relationship Tests"
        )
        self.position = JobPosition.objects.create(
            position_title="Recruitment Relationship Position"
        )
        self.vacancy = JobVacancy.objects.create(
            department=self.department,
            position=self.position,
            title="Relationship Test Vacancy",
            description="Test description",
            requirements="Test requirements",
            date_posted=date.today(),
            closing_date=date.today() + timedelta(days=14),
        )
        self.applicant = Applicant.objects.create(
            first_name="Relationship",
            last_name="Applicant",
            email="relationship.applicant@example.com",
            cv_path="cvs/relationship.pdf",
            consent_given=True,
            consent_date=__import__(
                "django.utils.timezone", fromlist=["now"]
            ).now(),
        )

    def test_department_deletion_is_protected_by_vacancy(self):
        with self.assertRaises(ProtectedError):
            self.department.delete()

    def test_position_deletion_is_protected_by_vacancy(self):
        with self.assertRaises(ProtectedError):
            self.position.delete()

    def test_vacancy_deletion_cascades_to_applications(self):
        application = Application.objects.create(
            vacancy=self.vacancy,
            applicant=self.applicant,
        )
        self.vacancy.delete()
        self.assertFalse(
            Application.objects.filter(pk=application.pk).exists()
        )

    def test_applicant_deletion_cascades_to_applications(self):
        application = Application.objects.create(
            vacancy=self.vacancy,
            applicant=self.applicant,
        )
        self.applicant.delete()
        self.assertFalse(
            Application.objects.filter(pk=application.pk).exists()
        )
