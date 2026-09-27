"""Course content, enrollment, and assessed exam submissions."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.timezone import now


class Instructor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_time = models.BooleanField(default=True)
    total_learners = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user.get_username()


class Learner(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    OCCUPATION_CHOICES = [("student", "Student"), ("developer", "Developer"),
                          ("data_scientist", "Data Scientist"), ("dba", "Database Admin")]
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, default="student")
    social_link = models.URLField(blank=True)

    def __str__(self):
        return f"{self.user.get_username()}, {self.occupation}"


class Course(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="course_images/", blank=True)
    description = models.CharField(max_length=1000)
    pub_date = models.DateField(default=now)
    instructors = models.ManyToManyField(Instructor, blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Enrollment")
    total_enrollment = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        ordering = ("order", "pk")

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    COURSE_MODES = [("audit", "Audit"), ("honor", "Honor"), ("beta", "Beta")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=now)
    mode = models.CharField(max_length=5, choices=COURSE_MODES, default="audit")
    rating = models.FloatField(default=5, validators=[MinValueValidator(0), MaxValueValidator(5)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "course"), name="unique_enrollment")]

    def __str__(self):
        return f"{self.user.get_username()} — {self.course.name}"


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.CharField(max_length=200)
    grade = models.PositiveIntegerField(default=50, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ("pk",)
        constraints = [models.CheckConstraint(condition=models.Q(grade__gt=0), name="positive_question_grade")]

    def __str__(self):
        return self.content

    def is_get_score(self, selected_ids):
        """Award credit only for the exact correct set; selecting every choice fails."""
        choices = list(self.choice_set.all())
        correct = {choice.pk for choice in choices if choice.is_correct}
        selected = set(selected_ids) & {choice.pk for choice in choices}
        return bool(correct) and selected == correct


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    content = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return self.content


class Submission(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    choices = models.ManyToManyField(Choice, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(default=0)
    possible_score = models.PositiveIntegerField(default=0)

    @property
    def percentage(self):
        return round(100 * self.score / self.possible_score) if self.possible_score else 0

    def __str__(self):
        return f"Submission {self.pk}: {self.score}/{self.possible_score}"
