from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION enforce_employee_minimum_age()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.date_of_birth >
                       (CURRENT_DATE - INTERVAL '18 years')::date THEN
                        RAISE EXCEPTION
                            'Employees must be at least 18 years old.'
                            USING ERRCODE = 'check_violation';
                    END IF;

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER employee_minimum_age_trigger
                BEFORE INSERT OR UPDATE OF date_of_birth
                ON employees_employee
                FOR EACH ROW
                EXECUTE FUNCTION enforce_employee_minimum_age();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS employee_minimum_age_trigger
                ON employees_employee;

                DROP FUNCTION IF EXISTS enforce_employee_minimum_age();
            """,
        ),
    ]
