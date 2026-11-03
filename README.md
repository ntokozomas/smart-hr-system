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

## Run

    python manage.py runserver

Then open http://127.0.0.1:8000/admin

## Rules

- Work on your own branch, e.g. feature/leave. Never push straight to main.
- Before pushing: ruff check . --fix && ruff format .  and  python manage.py test
- Open a pull request; one other person reviews before merging.
- Pull main every morning: git pull origin main
- Never commit .env
