# OnlineCourse assessment application

IBM Django final project by Justin Williams, based on the IBM Developer Skills Network starter. Learners browse lessons, enroll, submit multiple-choice assessments, and review their own results. Staff manage courses, lessons, questions, and choices in Django admin.

## Run locally

Use Python 3.12 or newer. The application was verified with Django 5.2.17.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_DEBUG=1
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8012
```

Open http://127.0.0.1:8012/ for the course and http://127.0.0.1:8012/admin/ for administration. The development-only seed command creates a Learning Django course with two lessons and two assessment questions. It writes a randomly generated local administrator password to `.demo-credentials.json`; read that local file to sign in as `course_admin`. The file, development secret, and database are ignored by Git. The command refuses to run when debug mode is disabled.

In the course, choose **Enroll in course**, expand **Start Exam**, select answers, and submit. Scores are calculated on the server. Each question earns points only when the selected choices exactly match its correct choices. A score of 70% passes. Empty answers receive no credit.

## Implementation

- `onlinecourse/models.py` defines courses, lessons, enrollments, questions, choices, and scored submissions. A database constraint prevents duplicate enrollment.
- `onlinecourse/admin.py` exposes course and question inlines and read-only submission scores.
- `onlinecourse/views.py` validates submitted choice IDs, requires enrollment, saves submissions atomically, and limits result access to the submission owner and matching course.
- `onlinecourse/urls.py` defines named enrollment, submission, and result routes.
- `onlinecourse/templates/onlinecourse/course_details_bootstrap.html` renders lessons and the assessment form; `exam_result_bootstrap.html` renders the score and detailed feedback.
- Bootstrap 5.3.8 CSS is vendored with its license header, so the UI does not need a third-party CDN at runtime.

Django's authentication forms and password validators handle account creation and sign-in. State-changing requests use POST and CSRF protection. Scores are stored at submission time; editing assessment content later can change the explanatory answer review, so instructors should avoid changing questions after accepting submissions.

## Verification

```sh
DJANGO_DEBUG=1 python manage.py check
DJANGO_DEBUG=1 python manage.py test onlinecourse
```

All 11 tests passed. They exercise exact scoring, incorrect and missing choices, foreign-course and malformed submissions, authentication and enrollment checks, private result access, CSRF and POST requirements, idempotent enrollment, unconfigured exams, and password validation. A Safari browser check also verified admin navigation, enrollment, assessment submission, and the 100/100 demo result. The demo score is application test data, not a Coursera project grade.

## Deployment configuration

Debug mode is off by default. Set a strong `DJANGO_SECRET_KEY`, an explicit comma-separated `DJANGO_ALLOWED_HOSTS`, and any required HTTPS origins in `DJANGO_CSRF_TRUSTED_ORIGINS`. Run migrations, create a real administrator, and run `python manage.py collectstatic`. Use a production WSGI server such as `gunicorn myproject.wsgi:application` behind an HTTPS endpoint configured to serve collected static files. Secure cookies, HTTPS redirects, and HSTS are enabled outside debug mode. Configure trusted proxy headers only for a proxy you control.

SQLite is the local default. For a multi-instance deployment, configure a supported shared database and durable uploaded-media storage, add rate limiting at the deployment edge, and arrange backups before accepting real learner data. Do not deploy the demonstration credentials or enable debug mode publicly.
