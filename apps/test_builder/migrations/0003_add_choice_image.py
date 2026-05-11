from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_builder', '0002_add_question_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='choice',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='choice_images/%Y/%m/', verbose_name='Rasm (ixtiyoriy)'),
        ),
    ]
