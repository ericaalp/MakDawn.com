from django import forms

from .models import UploadJob


class UploadForm(forms.ModelForm):
    subject_name = forms.CharField(
        max_length=160, required=False,
        label="Fan nomi",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Masalan: Oliy matematika, Fizika...",
        }),
    )
    test_title = forms.CharField(
        max_length=200, required=False,
        label="Test nomi (ixtiyoriy)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Bo'sh qoldirilsa fayl nomidan olinadi",
        }),
    )

    class Meta:
        model = UploadJob
        fields = ('file',)
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.docx,.xlsx,.pdf,.txt,.png,.jpg,.jpeg,.webp,.bmp',
            }),
        }
