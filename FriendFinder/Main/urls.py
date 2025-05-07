from django.urls import path
from . import views

urlpatterns = [
    path('profiles/', views.profile_list, name='profile-list'),
    path('profiles/<int:pk>/', views.profile_detail, name='profile-detail'),
    path('likes/', views.like_create, name='like-create'),
    path('likes/<int:pk>/', views.like_detail, name='like-detail'),
]