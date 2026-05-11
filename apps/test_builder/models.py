from django.conf import settings
from django.db import models
from django.urls import reverse


class Subject(models.Model):
    """Fan (Oliy matematika, Diskret tuzilmalar, Matematik tahlil...)."""
    name = models.CharField("Fan nomi", max_length=160, unique=True)
    slug = models.SlugField(max_length=160, unique=True)

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
        ordering = ['name']

    def __str__(self):
        return self.name


class Test(models.Model):
    """O'qituvchi yaratgan test bazasi."""

    DIFFICULTY = [
        ('easy', 'Oson'),
        ('medium', "O'rta"),
        ('hard', 'Qiyin'),
    ]

    title = models.CharField("Test nomi", max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='tests', verbose_name="Fan")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='tests', verbose_name="O'qituvchi")
    description = models.TextField("Tavsif", blank=True)
    difficulty = models.CharField("Darajasi", max_length=10, choices=DIFFICULTY, default='medium')
    time_limit = models.PositiveIntegerField("Vaqt (daqiqa)", default=45)
    shuffle_questions = models.BooleanField("Savollarni aralashtirish", default=True)
    shuffle_choices = models.BooleanField("Javoblarni aralashtirish", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('test_builder:detail', args=[self.pk])

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all())


class Question(models.Model):
    """Test savoli."""

    QTYPE = [
        ('single', 'Bitta to\'g\'ri javob'),
        ('multiple', "Bir nechta to'g'ri javob"),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField("Savol matni", help_text="LaTeX uchun $...$ ishlating")
    image = models.ImageField("Rasm (ixtiyoriy)", upload_to='question_images/%Y/%m/', blank=True, null=True)
    qtype = models.CharField("Savol turi", max_length=10, choices=QTYPE, default='single')
    points = models.PositiveSmallIntegerField("Ball", default=1)
    order = models.PositiveIntegerField("Tartib", default=0)
    explanation = models.TextField("Izoh (ixtiyoriy)", blank=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self):
        return f"#{self.order or self.pk}: {self.text[:60]}"


class Choice(models.Model):
    """Savol uchun javob varianti."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField("Variant matni", max_length=500, blank=True)
    image = models.ImageField("Rasm (ixtiyoriy)", upload_to='choice_images/%Y/%m/', blank=True, null=True)
    is_correct = models.BooleanField("To'g'ri javob", default=False)
    order = models.PositiveSmallIntegerField("Tartib", default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        mark = "✓" if self.is_correct else " "
        return f"[{mark}] {self.text[:60]}"
