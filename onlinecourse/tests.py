"""Exercise scoring, authorization, CSRF, malformed input, and enrollment behavior."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import Choice, Course, Enrollment, Question, Submission


class ExamWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("learner", password="ExampleTestPassword!123")
        cls.other = get_user_model().objects.create_user("other", password="OtherTestPassword!123")
        cls.course = Course.objects.create(name="Learning Django", description="Course description")
        cls.question = Question.objects.create(course=cls.course, content="Choose the frameworks", grade=100)
        cls.yes = Choice.objects.create(question=cls.question, content="Django", is_correct=True)
        cls.also = Choice.objects.create(question=cls.question, content="Flask", is_correct=True)
        cls.no = Choice.objects.create(question=cls.question, content="HTML", is_correct=False)
        cls.enrollment = Enrollment.objects.create(user=cls.user, course=cls.course)
        cls.url = reverse("onlinecourse:submit", args=[cls.course.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def choices(self, *choices):
        return {f"choice_{choice.pk}": str(choice.pk) for choice in choices}

    def test_exact_correct_choices_pass_and_render(self):
        response = self.client.post(self.url, self.choices(self.yes, self.also), follow=True)
        submission = Submission.objects.get()
        self.assertEqual(submission.percentage, 100)
        self.assertContains(response, "Congratulations")
        self.assertContains(response, "Score 100/100")
        self.assertContains(response, "Correct answer: Django")

    def test_selecting_wrong_extra_choice_fails(self):
        response = self.client.post(self.url, self.choices(self.yes, self.also, self.no), follow=True)
        self.assertEqual(Submission.objects.get().score, 0)
        self.assertContains(response, "Wrong answer: HTML")

    def test_missing_correct_choice_and_blank_submission_fail(self):
        self.client.post(self.url, self.choices(self.yes))
        self.client.post(self.url, {})
        self.assertEqual(list(Submission.objects.values_list("score", flat=True)), [0, 0])

    def test_cross_course_choice_rejected_without_record(self):
        other_course = Course.objects.create(name="Other course", description="Other")
        q = Question.objects.create(course=other_course, content="Foreign")
        foreign = Choice.objects.create(question=q, content="Foreign choice", is_correct=True)
        self.assertEqual(self.client.post(self.url, self.choices(foreign)).status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_malformed_and_duplicate_values_rejected(self):
        for payload in [{"choice_abc": "abc"}, {"choice_0": "0"}, {f"choice_{self.yes.pk}": [str(self.yes.pk), str(self.no.pk)]}]:
            self.assertEqual(self.client.post(self.url, payload).status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_result_is_private_and_course_scoped(self):
        self.client.post(self.url, self.choices(self.yes, self.also))
        submission = Submission.objects.get()
        url = reverse("onlinecourse:exam_result", args=[self.course.pk, submission.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.user)
        wrong_url = reverse("onlinecourse:exam_result", args=[self.course.pk + 10, submission.pk])
        self.assertEqual(self.client.get(wrong_url).status_code, 404)

    def test_authentication_and_enrollment_required(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {}).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url, {}).status_code, 404)
        self.assertFalse(Submission.objects.exists())

    def test_mutations_require_post_and_csrf(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.url, self.choices(self.yes)).status_code, 403)

    def test_enrollment_is_idempotent(self):
        self.client.force_login(self.other)
        url = reverse("onlinecourse:enroll", args=[self.course.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(Enrollment.objects.filter(user=self.other, course=self.course).count(), 1)
        self.course.refresh_from_db()
        self.assertEqual(self.course.total_enrollment, 1)

    def test_unconfigured_exam_cannot_award_credit(self):
        self.question.choice_set.update(is_correct=False)
        self.assertFalse(self.question.is_get_score(set()))
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_registration_uses_password_validation(self):
        response = self.client.post(reverse("onlinecourse:registration"), {
            "username": "newlearner", "password1": "123", "password2": "123"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="newlearner").exists())
