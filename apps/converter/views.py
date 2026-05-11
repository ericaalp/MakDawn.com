import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from apps.test_builder.models import Choice, Question, Subject, Test

from .forms import UploadForm
from .models import UploadJob
from .parsers import parse_file
from . import openai_service


def _parse_job(job):
    if openai_service.is_configured():
        return openai_service.run_for_file(job.file, job.original_name)
    return parse_file(job.file, job.original_name)


def _get_or_create_subject(name: str):
    """Fan nomini topadi yoki yaratadi (slug avtomatik)."""
    name = (name or '').strip()[:160]
    if not name:
        return None
    base_slug = slugify(name) or 'fan'
    slug = base_slug
    i = 1
    while Subject.objects.filter(slug=slug).exclude(name=name).exists():
        slug = f'{base_slug}-{i}'
        i += 1
    subject, _ = Subject.objects.get_or_create(name=name, defaults={'slug': slug})
    return subject


@login_required
def upload(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.owner = request.user
            job.original_name = request.FILES['file'].name
            job.save()
            try:
                parsed = _parse_job(job)
                valid = [q for q in parsed if q.is_valid]
                job.parsed_count = len(valid)

                if not valid:
                    job.status = 'failed'
                    job.error = "Savollar topilmadi yoki to'g'ri javob belgilanmagan."
                    job.save()
                    messages.error(request, "Savollar topilmadi. Format to'g'riligini tekshiring.")
                    return redirect('converter:upload')

                # To'g'ridan-to'g'ri testga aylantirib DB ga saqlaymiz
                subject = _get_or_create_subject(form.cleaned_data.get('subject_name', ''))
                title = (
                    form.cleaned_data.get('test_title', '').strip()
                    or job.original_name.rsplit('.', 1)[0]
                )

                with transaction.atomic():
                    test = Test.objects.create(
                        title=title,
                        owner=request.user,
                        subject=subject,
                        description=f"Fayldan import qilindi: {job.original_name}",
                    )
                    for idx, q in enumerate(valid, 1):
                        correct_count = sum(1 for c in q.choices if c.is_correct)
                        qtype = 'multiple' if correct_count > 1 else 'single'
                        question = Question.objects.create(
                            test=test, text=q.text,
                            qtype=qtype, order=idx,
                        )
                        for c_idx, c in enumerate(q.choices, 1):
                            Choice.objects.create(
                                question=question, text=c.text,
                                is_correct=c.is_correct, order=c_idx,
                            )
                    job.test = test
                    job.status = 'imported'
                    job.save()

                messages.success(
                    request,
                    f"{len(valid)} ta savol muvaffaqiyatli import qilindi. "
                    "Savollarni tahrirlang va kerakli formatda yuklab oling."
                )
                return redirect('test_builder:detail', pk=test.pk)

            except Exception as exc:
                job.status = 'failed'
                job.error = str(exc)
                job.save()
                messages.error(request, f"Xato: {exc}")
                return redirect('converter:upload')
    else:
        form = UploadForm()

    return render(request, 'converter/upload.html', {
        'form': form,
        'jobs': UploadJob.objects.filter(owner=request.user).select_related('test')[:10],
        'ai_active': openai_service.is_configured(),
    })


@login_required
def preview(request, pk):
    """Arxivdagi eski preview — endi faqat test_detail ga yo'naltiradi."""
    job = get_object_or_404(UploadJob, pk=pk, owner=request.user)
    if job.test:
        return redirect('test_builder:detail', pk=job.test.pk)
    messages.info(request, "Bu fayl hali testga aylantirilmagan.")
    return redirect('converter:upload')
