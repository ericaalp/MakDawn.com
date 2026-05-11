from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import TeacherLoginForm, TeacherRegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:dashboard')
    else:
        form = TeacherRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


class TeacherLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = TeacherLoginForm
    redirect_authenticated_user = True


class TeacherLogoutView(LogoutView):
    next_page = reverse_lazy('core:landing')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'teacher': request.user})
