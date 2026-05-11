from django.conf import settings
from django.db import models


class UploadJob(models.Model):
    """Foydalanuvchi yuklagan fayl va parse natijasi."""
    STATUS = [
        ('pending', 'Kutilmoqda'),
        ('parsed', "Parse qilindi"),
        ('failed', 'Xato'),
        ('imported', 'Testga aylantirildi'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='upload_jobs')
    file = models.FileField("Fayl", upload_to='uploads/%Y/%m/')
    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS, default='pending')
    parsed_count = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    test = models.ForeignKey('test_builder.Test', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='source_jobs')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Yuklangan fayl"
        verbose_name_plural = "Yuklangan fayllar"

    def __str__(self):
        return self.original_name
