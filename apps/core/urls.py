from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('help/', views.help_view, name='help'),
    path('settings/', views.settings_view, name='settings'),
]
