"""Create reproducible course content and a local-only demonstration login."""
import json
import os
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from onlinecourse.models import Course, Instructor, Lesson, Question, Choice


class Command(BaseCommand):
    help = "Seed a local development course and an admin demo account."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo seeding is restricted to DJANGO_DEBUG=1.")
        credentials = settings.BASE_DIR / ".demo-credentials.json"
        user, created = get_user_model().objects.get_or_create(username="course_admin")
        if created:
            password = secrets.token_urlsafe(24)
            user.set_password(password)
            user.first_name = "Justin"
            user.last_name = "Williams"
            user.is_staff = user.is_superuser = True
            user.save()
            with open(credentials, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
                json.dump({"username": user.username, "password": password}, output)
        instructor, _ = Instructor.objects.get_or_create(user=user, defaults={"total_learners": 0})
        course, _ = Course.objects.get_or_create(name="Learning Django", defaults={
            "description": "Build database-driven web applications with Django, the Python web framework.",
            "pub_date": timezone.localdate(),
        })
        course.instructors.add(instructor)
        Lesson.objects.get_or_create(course=course, order=0, defaults={"title": "What is Django?", "content":
            "Django is a high-level Python web framework. Its models describe database records, views handle requests, and templates render HTML."})
        Lesson.objects.get_or_create(course=course, order=1, defaults={"title": "Models, views, and templates", "content":
            "Django's ORM maps Python objects to database rows. Views query those models and pass context to templates. Forms protect state-changing requests using CSRF tokens."})
        question, _ = Question.objects.get_or_create(course=course, content="Is Django a Python framework?", defaults={"grade": 50})
        Choice.objects.get_or_create(question=question, content="Yes", defaults={"is_correct": True})
        Choice.objects.get_or_create(question=question, content="No", defaults={"is_correct": False})
        question, _ = Question.objects.get_or_create(course=course, content="Which component maps Python objects to database rows?", defaults={"grade": 50})
        Choice.objects.get_or_create(question=question, content="Object-relational mapper (ORM)", defaults={"is_correct": True})
        Choice.objects.get_or_create(question=question, content="CSS stylesheet", defaults={"is_correct": False})
        self.stdout.write(self.style.SUCCESS("Demo course ready. Login is saved in the ignored .demo-credentials.json file."))
