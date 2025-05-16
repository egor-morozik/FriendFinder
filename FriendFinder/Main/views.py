from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import UserProfile, Like, Match, Message, Interest, City
from django.contrib import messages

@login_required
def profile_list(request):
    users = User.objects.all()
    profiles = UserProfile.objects.all()
    current_user = request.user
    matches = Match.objects.filter(user1=current_user) | Match.objects.filter(user2=current_user)
    matched_user_ids = set()
    for match in matches:
        if match.user1 == current_user:
            matched_user_ids.add(match.user2.id)
        else:
            matched_user_ids.add(match.user1.id)
    sent_likes = Like.objects.filter(from_user=current_user, is_active=True)
    sent_like_user_ids = {like.to_user.id for like in sent_likes}
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
        existing_match = Match.objects.filter(user1=current_user, user2=other_user).first() or \
                        Match.objects.filter(user1=other_user, user2=current_user).first()
        if not existing_match:
            like_from_current = Like.objects.filter(from_user=current_user, to_user=other_user, is_active=True).exists()
            like_from_other = Like.objects.filter(from_user=other_user, to_user=current_user, is_active=True).exists()
            if like_from_current and like_from_other:
                Match.objects.create(user1=current_user, user2=other_user, is_active=True)
                messages.success(request, f"Мэтч с {other_user.username} создан!")
            elif not like_from_current:
                Like.objects.create(from_user=current_user, to_user=other_user, is_active=True)
                messages.info(request, f"Лайк отправлен {other_user.username}. Ожидаем ответа.")
        else:
            messages.info(request, f"Мэтч с {other_user.username} уже существует.")
        return redirect('profile-list')
    return redirect('profile-list')

@login_required
def profile_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(UserProfile, user=user)
    current_user = request.user
    is_own_profile = (current_user == user)
    matches = Match.objects.filter(user1=current_user) | Match.objects.filter(user2=current_user)
    matched_user_ids = set()
    for match in matches:
        if match.user1 == current_user:
            matched_user_ids.add(match.user2.id)
        else:
            matched_user_ids.add(match.user1.id)
    sent_likes = Like.objects.filter(from_user=current_user, is_active=True)
    sent_like_user_ids = {like.to_user.id for like in sent_likes}
    interests = profile.interests.all()  # Получаем список интересов как объекты
    context = {
        'profile': profile,
        'is_own_profile': is_own_profile,
        'matched_user_ids': matched_user_ids,
        'sent_like_user_ids': sent_like_user_ids,
        'user_id': user_id,
        'interests': interests,
    }
    return render(request, 'profiles/profile_detail.html', context)

@login_required
def edit_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    cities = City.objects.all()  # Получаем все города
    if request.method == 'POST':
        profile.name = request.POST.get('name', profile.name)
        profile.age = request.POST.get('age', profile.age)
        profile.bio = request.POST.get('bio', profile.bio)
        city_id = request.POST.get('city')  # Получаем ID города
        if city_id:
            city = get_object_or_404(City, id=city_id)
            profile.location = city
        else:
            profile.location = None
        profile.status = request.POST.get('status', profile.status)
        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']
        
        existing_interests = set(profile.interests.values_list('name', flat=True))
        new_interests = request.POST.getlist('interests')
        for interest_name in new_interests:
            interest_name = interest_name.strip()
            if interest_name and interest_name not in existing_interests:
                interest, created = Interest.objects.get_or_create(name=interest_name)
                profile.interests.add(interest)

        profile.save()
        messages.success(request, "Профиль успешно обновлен!")
        return redirect('profile-detail', user_id=request.user.id)
    context = {'profile': profile, 'cities': cities}
    return render(request, 'profiles/edit_profile.html', context)

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

def like_create(request):
    return render(request, 'profiles/like_create.html')

def like_detail(request, pk):
    return render(request, 'profiles/like_detail.html', {'pk': pk})

def register(request):
    if request.user.is_authenticated:
        return redirect('profile-list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, name=user.username, age=18)  # Создаем профиль по умолчанию
            login(request, user)
            return redirect('profile-list')
    else:
        form = UserCreationForm()
    return render(request, 'profiles/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile-list')
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

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('login')