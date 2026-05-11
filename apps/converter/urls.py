from django.urls import path
from . import views

app_name = 'converter'

urlpatterns = [
    path('', views.upload, name='upload'),
    path('<int:pk>/preview/', views.preview, name='preview'),
]
