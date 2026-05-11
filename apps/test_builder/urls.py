from django.urls import path
from . import views

app_name = 'test_builder'

urlpatterns = [
    path('', views.test_list, name='list'),
    path('create/', views.create_hub, name='create_hub'),
    path('create/manual/', views.test_create, name='create'),
    path('create/ai/', views.ai_generate, name='ai_generate'),
    path('create/ai/preview/<str:token>/', views.ai_preview, name='ai_preview'),
    path('create/ai/save/<str:token>/', views.ai_save, name='ai_save'),
    path('<int:pk>/', views.test_detail, name='detail'),
    path('<int:pk>/edit/', views.test_edit, name='edit'),
    path('<int:pk>/delete/', views.test_delete, name='delete'),
    path('<int:pk>/export/<str:fmt>/', views.test_export, name='export'),
    path('<int:test_pk>/questions/add/', views.question_create, name='question_create'),
    path('questions/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('questions/<int:pk>/delete/', views.question_delete, name='question_delete'),
]
