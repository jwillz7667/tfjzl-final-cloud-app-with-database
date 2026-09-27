"""Authenticated enrollment, validated submissions, and owner-only exam results."""
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.views import generic
from .forms import RegistrationForm
from .models import Course, Enrollment, Question, Choice, Submission


@require_http_methods(["GET", "POST"])
def registration_request(request):
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("onlinecourse:index")
    return render(request, "onlinecourse/user_registration_bootstrap.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_request(request):
    form = AuthenticationForm(request, data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("onlinecourse:index")
    return render(request, "onlinecourse/user_login_bootstrap.html", {"form": form})


@require_POST
def logout_request(request):
    logout(request)
    return redirect("onlinecourse:index")


class CourseListView(generic.ListView):
    model = Course
    context_object_name = "course_list"
    template_name = "onlinecourse/course_list_bootstrap.html"
    queryset = Course.objects.order_by("-pub_date", "pk")


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_details_bootstrap.html"
    queryset = Course.objects.prefetch_related("lesson_set", "question_set__choice_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_enrolled"] = user.is_authenticated and Enrollment.objects.filter(
            user=user, course=self.object).exists()
        return context


@login_required
@require_POST
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    with transaction.atomic():
        _, created = Enrollment.objects.get_or_create(user=request.user, course=course, defaults={"mode": "honor"})
        if created:
            Course.objects.filter(pk=course.pk).update(total_enrollment=F("total_enrollment") + 1)
    return redirect("onlinecourse:course_details", pk=course.pk)


def extract_answers(request):
    """Parse every submitted choice, rejecting ambiguous or malformed fields."""
    selected = set()
    for key in request.POST:
        if key.startswith("choice_"):
            values = request.POST.getlist(key)
            if len(values) != 1 or not values[0].isascii() or not values[0].isdigit():
                raise ValueError("Invalid exam choice.")
            choice_id = int(values[0])
            if key != f"choice_{choice_id}" or choice_id <= 0:
                raise ValueError("Invalid exam choice.")
            selected.add(choice_id)
    return selected


@login_required
@require_POST
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    try:
        selected_ids = extract_answers(request)
    except ValueError:
        return HttpResponseBadRequest("Invalid exam choice. Please reopen the exam and try again.")
    questions = list(Question.objects.filter(course=course).prefetch_related("choice_set"))
    if not questions or any(not any(c.is_correct for c in q.choice_set.all()) for q in questions):
        return HttpResponseBadRequest("This exam is not yet ready for submissions.")
    allowed_ids = set(Choice.objects.filter(question__course=course).values_list("pk", flat=True))
    if not selected_ids <= allowed_ids:
        return HttpResponseBadRequest("All selected choices must belong to this course.")
    # Validate everything before creating a submission; an invalid request leaves no partial record.
    with transaction.atomic():
        submission = Submission.objects.create(
            enrollment=enrollment,
            score=sum(q.grade for q in questions if q.is_get_score(selected_ids)),
            possible_score=sum(q.grade for q in questions),
        )
        submission.choices.set(selected_ids)
    return redirect("onlinecourse:exam_result", course_id=course.pk, submission_id=submission.pk)


@login_required
@require_http_methods(["GET"])
def show_exam_result(request, course_id, submission_id):
    # Both the URL course and signed-in owner must match the stored enrollment.
    submission = get_object_or_404(
        Submission.objects.select_related("enrollment__course").prefetch_related("choices"),
        pk=submission_id, enrollment__course_id=course_id, enrollment__user=request.user,
    )
    course = submission.enrollment.course
    selected_ids = {c.pk for c in submission.choices.all()}
    results = []
    for question in Question.objects.filter(course=course).prefetch_related("choice_set"):
        results.append({"question": question, "correct": question.is_get_score(selected_ids),
                        "answers": [{"choice": c, "selected": c.pk in selected_ids}
                                    for c in question.choice_set.all()]})
    return render(request, "onlinecourse/exam_result_bootstrap.html", {
        "course": course, "submission": submission, "grade": submission.percentage,
        "passed": submission.percentage >= 70, "results": results,
    })
