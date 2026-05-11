from django.contrib.auth.models import AbstractUser
from django.db import models


class Teacher(AbstractUser):
    """O'qituvchi profili — ro'yxatdan bir martalik o'tadi."""

    middle_name = models.CharField("Otasining ismi", max_length=80, blank=True)
    phone = models.CharField("Telefon", max_length=20, blank=True)
    university = models.CharField("OTM", max_length=160, blank=True)
    faculty = models.CharField("Fakultet", max_length=160, blank=True)
    department = models.CharField("Kafedra", max_length=160, blank=True)
    position = models.CharField("Lavozim", max_length=120, blank=True)
    avatar = models.ImageField("Rasm", upload_to='avatars/', blank=True, null=True)

    class Meta:
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p).strip() or self.username
