from django.contrib import admin
from .models import Subject, Test, Question, Choice


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'test', 'qtype', 'points')
    list_filter = ('qtype', 'test__subject')
    inlines = [ChoiceInline]


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'owner', 'question_count', 'updated_at')
    list_filter = ('subject', 'difficulty')
    search_fields = ('title', 'description')
    inlines = [QuestionInline]
