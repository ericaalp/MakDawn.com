from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('middle_name', 'phone', 'university', 'faculty',
                       'department', 'position', 'avatar'),
        }),
    )
    list_display = ('username', 'email', 'last_name', 'first_name', 'university', 'is_staff')
