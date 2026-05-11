from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render


def landing(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/landing.html')


@login_required
def dashboard(request):
    from apps.test_builder.models import Test
    from apps.converter.models import UploadJob
    tests_qs = Test.objects.filter(owner=request.user).annotate(q_count=Count('questions'))
    stats = {
        'tests_count': tests_qs.count(),
        'converted_count': UploadJob.objects.filter(owner=request.user, status='imported').count(),
        'questions_count': tests_qs.aggregate(total=Sum('q_count'))['total'] or 0,
    }
    recent_tests = tests_qs.order_by('-updated_at')[:5]
    return render(request, 'core/dashboard.html', {
        'stats': stats, 'recent_tests': recent_tests,
    })


@login_required
def help_view(request):
    return render(request, 'core/help.html')


@login_required
def settings_view(request):
    from apps.accounts.forms import ProfileForm
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil saqlandi.")
            return redirect('core:settings')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'core/settings.html', {'form': form})
