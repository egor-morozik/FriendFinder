from django.urls import path
from . import views

urlpatterns = [
    path('profiles/', views.profile_list, name='profile-list'),
    path('profiles/<int:pk>/', views.profile_detail, name='profile-detail'),
    path('likes/', views.like_create, name='like-create'),
    path('likes/<int:pk>/', views.like_detail, name='like-detail'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/<int:user_id>/', views.chat, name='chat'),
    path('create-match/<int:user_id>/', views.create_match, name='create-match'),
]