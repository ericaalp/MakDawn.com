from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from apps.converter.models import UploadJob


@login_required
def archive_list(request):
    qs = UploadJob.objects.filter(owner=request.user).select_related('test')
    status = request.GET.get('status', '')
    if status in ('pending', 'parsed', 'failed', 'imported'):
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'archive/list.html', {
        'page_obj': page,
        'current_status': status,
    })
