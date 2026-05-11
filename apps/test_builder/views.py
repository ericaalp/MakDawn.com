from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

import secrets

from . import ai_service
from .exporters import FORMATS
from .forms import AIGenerateForm, ChoiceFormSet, QuestionForm, TestEditForm, TestForm
from .models import Choice, Question, Subject, Test


def _get_or_create_subject(name: str):
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
def create_hub(request):
    return render(request, 'test_builder/create_hub.html', {
        'ai_configured': ai_service.is_configured(),
    })


@login_required
def ai_generate(request):
    if request.method == 'POST':
        form = AIGenerateForm(request.POST)
        if form.is_valid():
            result = ai_service.generate_questions(
                subject=form.cleaned_data['subject'],
                topic=form.cleaned_data['topic'],
                count=form.cleaned_data['count'],
                difficulty=form.cleaned_data['difficulty'],
                sample_text=form.cleaned_data['sample_text'],
            )
            if not result.ok:
                messages.error(request, result.error or "AI hech narsa yaratmadi.")
                return render(request, 'test_builder/ai_form.html', {
                    'form': form, 'ai_configured': ai_service.is_configured(),
                })
            token = secrets.token_urlsafe(12)
            request.session[f'ai_{token}'] = {
                'questions': result.questions,
                'subject': form.cleaned_data['subject'],
                'topic': form.cleaned_data['topic'],
                'difficulty': form.cleaned_data['difficulty'],
                'save_subject_id': form.cleaned_data['save_subject'].pk if form.cleaned_data['save_subject'] else None,
            }
            return redirect('test_builder:ai_preview', token=token)
    else:
        form = AIGenerateForm()
    return render(request, 'test_builder/ai_form.html', {
        'form': form, 'ai_configured': ai_service.is_configured(),
    })


@login_required
def ai_preview(request, token):
    data = request.session.get(f'ai_{token}')
    if not data:
        messages.error(request, "Generatsiya ma'lumotlari topilmadi yoki muddati o'tib ketdi.")
        return redirect('test_builder:ai_generate')
    return render(request, 'test_builder/ai_preview.html', {
        'token': token, 'data': data, 'questions': data['questions'],
    })


@login_required
@require_POST
def ai_save(request, token):
    data = request.session.get(f'ai_{token}')
    if not data:
        messages.error(request, "Ma'lumotlar topilmadi.")
        return redirect('test_builder:ai_generate')

    title = request.POST.get('title') or f"{data['subject']} — {data['topic']}"
    test = Test.objects.create(
        title=title, owner=request.user,
        subject_id=data.get('save_subject_id'),
        difficulty=data.get('difficulty', 'medium'),
        description=f"AI yaratdi: {data['subject']} / {data['topic']}",
    )
    for idx, q_data in enumerate(data['questions'], 1):
        question = Question.objects.create(
            test=test, text=q_data['text'],
            qtype='single', order=idx,
            explanation=q_data.get('explanation', ''),
        )
        for c_idx, c_data in enumerate(q_data['choices'], 1):
            Choice.objects.create(
                question=question, text=c_data['text'],
                is_correct=c_data['is_correct'], order=c_idx,
            )
    request.session.pop(f'ai_{token}', None)
    messages.success(request, f"{len(data['questions'])} ta savol bilan test saqlandi.")
    return redirect('test_builder:detail', pk=test.pk)


@login_required
def test_list(request):
    tests = Test.objects.filter(owner=request.user).select_related('subject')
    return render(request, 'test_builder/list.html', {'tests': tests})


@login_required
def test_create(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.owner = request.user
            test.save()
            messages.success(request, "Test yaratildi. Endi savollar qo'shing.")
            return redirect('test_builder:detail', pk=test.pk)
    else:
        form = TestForm()
    return render(request, 'test_builder/form.html', {'form': form, 'title': 'Yangi test'})


@login_required
def test_detail(request, pk):
    test = get_object_or_404(Test, pk=pk, owner=request.user)
    questions = test.questions.prefetch_related('choices')
    return render(request, 'test_builder/detail.html', {
        'test': test, 'questions': questions, 'formats': FORMATS,
    })


@login_required
def test_edit(request, pk):
    test = get_object_or_404(Test, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = TestEditForm(request.POST)
        if form.is_valid():
            test.title = form.cleaned_data['title']
            test.subject = _get_or_create_subject(form.cleaned_data.get('subject_name', ''))
            test.save()
            messages.success(request, "Saqlandi.")
            return redirect('test_builder:detail', pk=test.pk)
    else:
        form = TestEditForm(initial={
            'title': test.title,
            'subject_name': test.subject.name if test.subject else '',
        })
    return render(request, 'test_builder/form.html', {
        'form': form, 'test': test,
    })


@login_required
@require_POST
def test_delete(request, pk):
    test = get_object_or_404(Test, pk=pk, owner=request.user)
    test.delete()
    messages.success(request, "Test o'chirildi.")
    return redirect('test_builder:list')


@login_required
def question_create(request, test_pk):
    test = get_object_or_404(Test, pk=test_pk, owner=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        formset = ChoiceFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            question = form.save(commit=False)
            question.test = test
            question.order = test.questions.count() + 1
            question.save()

            formset.instance = question
            formset.save()

            correct_count = question.choices.filter(is_correct=True).count()
            question.qtype = 'multiple' if correct_count > 1 else 'single'
            question.save(update_fields=['qtype'])

            messages.success(request, "Savol qo'shildi.")
            if 'save_and_add' in request.POST:
                return redirect('test_builder:question_create', test_pk=test.pk)
            return redirect('test_builder:detail', pk=test.pk)
    else:
        form = QuestionForm()
        formset = ChoiceFormSet()
    return render(request, 'test_builder/question_form.html', {
        'form': form, 'formset': formset, 'test': test,
    })


@login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk, test__owner=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES, instance=question)
        formset = ChoiceFormSet(request.POST, request.FILES, instance=question)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            correct_count = question.choices.filter(is_correct=True).count()
            question.qtype = 'multiple' if correct_count > 1 else 'single'
            question.save(update_fields=['qtype'])
            messages.success(request, "Savol saqlandi.")
            return redirect('test_builder:detail', pk=question.test.pk)
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)
    return render(request, 'test_builder/question_form.html', {
        'form': form, 'formset': formset, 'test': question.test, 'question': question,
    })


@login_required
@require_POST
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk, test__owner=request.user)
    test_pk = question.test.pk
    question.delete()
    messages.success(request, "Savol o'chirildi.")
    return redirect('test_builder:detail', pk=test_pk)


@login_required
def test_export(request, pk, fmt):
    test = get_object_or_404(Test, pk=pk, owner=request.user)
    if fmt not in FORMATS:
        raise Http404("Noma'lum format")
    if not test.questions.exists():
        messages.error(request, "Testda savollar yo'q — eksport imkonsiz.")
        return redirect('test_builder:detail', pk=pk)

    label, mime, ext, exporter = FORMATS[fmt]
    content = exporter(test)
    if isinstance(content, str):
        content = content.encode('utf-8')
    filename = f"{test.title.replace(' ', '_')}_{fmt}.{ext}"
    resp = HttpResponse(content, content_type=mime)
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp
