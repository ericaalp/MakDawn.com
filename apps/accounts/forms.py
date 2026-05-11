from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Teacher


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ('first_name', 'last_name', 'middle_name', 'email', 'phone',
                  'university', 'faculty', 'department', 'position', 'avatar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'form-control')


class TeacherRegistrationForm(UserCreationForm):
    class Meta:
        model = Teacher
        fields = (
            'username', 'email', 'last_name', 'first_name', 'middle_name',
            'phone', 'university', 'faculty', 'department', 'position',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'form-control')


class TeacherLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'form-control')
