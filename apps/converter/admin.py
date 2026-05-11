from django.contrib import admin
from .models import UploadJob


@admin.register(UploadJob)
class UploadJobAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'owner', 'status', 'parsed_count', 'test', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('created_at',)
