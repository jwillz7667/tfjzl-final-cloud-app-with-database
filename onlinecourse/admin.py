"""Manage all course content and inspect learner submissions."""
from django.contrib import admin
from .models import Course, Lesson, Instructor, Learner, Question, Choice, Submission


class ChoiceInline(admin.StackedInline):
    model = Choice
    extra = 2


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline, QuestionInline]
    list_display = ("name", "pub_date", "total_enrollment")
    search_fields = ("name", "description")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ("content", "course", "grade")
    list_filter = ("course",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "enrollment", "score", "possible_score", "submitted_at")
    readonly_fields = ("enrollment", "choices", "score", "possible_score", "submitted_at")

    def has_add_permission(self, request):
        return False


admin.site.register(Choice)
admin.site.register(Instructor)
admin.site.register(Learner)
