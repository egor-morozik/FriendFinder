from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import UserProfile, Like, Match, Message

@login_required
def profile_list(request):
    users = User.objects.all()
    profiles = UserProfile.objects.all()
    current_user = request.user
    # Получаем существующие мэтчи текущего пользователя
    matches = Match.objects.filter(user1=current_user) | Match.objects.filter(user2=current_user)
    matched_user_ids = set()
    for match in matches:
        if match.user1 == current_user:
            matched_user_ids.add(match.user2.id)
        else:
            matched_user_ids.add(match.user1.id)
    # Получаем лайки, отправленные текущим пользователем
    sent_likes = Like.objects.filter(from_user=current_user, is_active=True)
    sent_like_user_ids = {like.to_user.id for like in sent_likes}
    # Получаем лайки, полученные текущим пользователем
    received_likes = Like.objects.filter(to_user=current_user, is_active=True)
    received_like_user_ids = {like.from_user.id for like in received_likes}
    context = {
        'users': users,
        'profiles': profiles,
        'matched_user_ids': matched_user_ids,
        'sent_like_user_ids': sent_like_user_ids,
        'received_like_user_ids': received_like_user_ids,
    }
    return render(request, 'profiles/profile_list.html', context)

@login_required
def create_match(request, user_id):
    if request.method == 'POST':
        other_user = User.objects.get(id=user_id)
        current_user = request.user
        # Проверяем, нет ли уже мэтча
        existing_match = Match.objects.filter(user1=current_user, user2=other_user).first() or \
                        Match.objects.filter(user1=other_user, user2=current_user).first()
        if not existing_match:
            # Проверяем взаимные лайки
            like_from_current = Like.objects.filter(from_user=current_user, to_user=other_user, is_active=True).exists()
            like_from_other = Like.objects.filter(from_user=other_user, to_user=current_user, is_active=True).exists()
            if like_from_current and like_from_other:
                # Создаем мэтч
                Match.objects.create(user1=current_user, user2=other_user, is_active=True)
            else:
                # Создаем лайк от текущего пользователя, если его еще нет
                if not like_from_current:
                    Like.objects.create(from_user=current_user, to_user=other_user, is_active=True)
        return redirect('profile-list')
    return redirect('profile-list')

@login_required
def chat(request, user_id):
    other_user = User.objects.get(id=user_id)
    current_user = request.user
    match = Match.objects.filter(user1=current_user, user2=other_user).first() or \
            Match.objects.filter(user1=other_user, user2=current_user).first()
    messages = Message.objects.filter(match=match) if match else []
    if request.method == 'POST':
        content = request.POST.get('content', '')
        if match and content:
            Message.objects.create(match=match, sender=current_user, content=content)
            return redirect('chat', user_id=user_id)
    context = {'other_user': other_user, 'messages': messages, 'match': match}
    return render(request, 'profiles/chat.html', context)

def profile_detail(request, pk):
    return render(request, 'profiles/profile_detail.html', {'pk': pk})

def like_create(request):
    return render(request, 'profiles/like_create.html')

def like_detail(request, pk):
    return render(request, 'profiles/like_detail.html', {'pk': pk})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile-list')
    else:
        form = UserCreationForm()
    return render(request, 'profiles/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('profile-list')
    else:
        form = AuthenticationForm()
    return render(request, 'profiles/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')