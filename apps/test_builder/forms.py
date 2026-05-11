from django import forms
from django.forms import inlineformset_factory

from .models import Test, Question, Choice


class TestEditForm(forms.Form):
    """Faqat test nomi va fan nomini tahrirlash."""
    title = forms.CharField(
        max_length=200, label="Test nomi",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    subject_name = forms.CharField(
        max_length=160, required=False, label="Fan nomi",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Masalan: Oliy matematika",
        }),
    )


class TestForm(forms.ModelForm):
    """Qo'lda test yaratish uchun (to'liq forma)."""
    class Meta:
        model = Test
        fields = ('title', 'subject', 'description', 'difficulty',
                  'time_limit', 'shuffle_questions', 'shuffle_choices')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            else:
                field.widget.attrs.setdefault('class', 'form-control')


class QuestionForm(forms.ModelForm):
    """Savol matni + ixtiyoriy rasm."""
    class Meta:
        model = Question
        fields = ('text', 'image')
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': "Savol matni... (formulalar uchun $x^2$ LaTeX ishlatiladi)",
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
        labels = {
            'text': "Savol matni",
            'image': "Rasm (formulali yoki geometrik savollarda)",
        }


class AIGenerateForm(forms.Form):
    DIFFICULTY = [('easy', 'Oson'), ('medium', "O'rta"), ('hard', 'Qiyin')]

    subject = forms.CharField(label="Fan", max_length=160,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Oliy matematika"}))
    topic = forms.CharField(label="Mavzu", max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Aniq integrallar"}))
    count = forms.IntegerField(label="Savollar soni", min_value=3, max_value=30, initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))
    difficulty = forms.ChoiceField(label="Qiyinlik", choices=DIFFICULTY, initial='medium',
        widget=forms.Select(attrs={'class': 'form-control'}))
    sample_text = forms.CharField(label="Namuna matn (ixtiyoriy)", required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
            'placeholder': "Mavjud savollar uslubida yaratilishini xohlasangiz namuna kiriting..."}))
    save_subject = forms.ModelChoiceField(label="Fan (saqlash uchun)", required=False,
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Saqlanganda tanlangan fanga biriktiriladi.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Subject
        self.fields['save_subject'].queryset = Subject.objects.all()


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ('text', 'image', 'is_correct')
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Variant matni (rasm bo'lsa ixtiyoriy)",
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control form-control-sm',
                'accept': 'image/*',
            }),
        }
        labels = {'text': '', 'image': '', 'is_correct': "To'g'ri"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('DELETE'):
            return cleaned
        text = (cleaned.get('text') or '').strip()
        image = cleaned.get('image')
        # Mavjud instance ning rasmi saqlanib qolishi mumkin (False qaytmaydi)
        existing_image = getattr(self.instance, 'image', None) and self.instance.pk
        if self.has_changed() and not text and not image and not existing_image:
            pass  # bo'sh extra qator — formset darajasida hisoblanadi
        return cleaned


class BaseChoiceFormSet(forms.BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return
        filled = 0
        for form in self.forms:
            if not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            text = (form.cleaned_data.get('text') or '').strip()
            image = form.cleaned_data.get('image')
            existing_image = (
                getattr(form.instance, 'image', None) and
                form.instance.pk and
                form.cleaned_data.get('image') is not False
            )
            if text or image or existing_image:
                filled += 1
        if filled < self.min_num:
            raise forms.ValidationError(
                f"Kamida {self.min_num} ta javob varianti kiritilishi kerak (matn yoki rasm)."
            )


ChoiceFormSet = inlineformset_factory(
    Question, Choice,
    form=ChoiceForm,
    formset=BaseChoiceFormSet,
    fields=('text', 'image', 'is_correct'),
    extra=4, min_num=2, can_delete=True, validate_min=False,
)
