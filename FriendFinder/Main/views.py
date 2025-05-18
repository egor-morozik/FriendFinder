import json
from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import UserProfile, Like, Match, Message, Interest, City
from django.contrib import messages
from django.core.cache import cache
import random

@login_required
def profile_list(request):
    current_profile = UserProfile.objects.get(user=request.user)
    current_user_interests = set(current_profile.interests.values_list('name', flat=True))
    
    profiles = UserProfile.objects.exclude(user=request.user).select_related('user', 'location')
    
    city_filter = request.GET.get('city', '')
    if city_filter:
        profiles = profiles.filter(location__name__iexact=city_filter)
    else:
        if current_profile.location:
            city_filter = current_profile.location.name
    
    interest_filters = request.GET.getlist('interests', [])
    if interest_filters:
        profiles = profiles.filter(interests__name__in=interest_filters).distinct()
    
    age_range = request.GET.get('age_range', '')
    if age_range and current_profile.age:
        try:
            age_range = int(age_range)
            min_age = max(0, current_profile.age - age_range)
            max_age = current_profile.age + age_range
            profiles = profiles.filter(age__gte=min_age, age__lte=max_age)
        except ValueError:
            pass  
    
    sort_by = request.GET.get('sort', '')
    if sort_by == 'interests':
        profiles = sorted(profiles, key=lambda p: len(current_user_interests.intersection(
            set(p.interests.values_list('name', flat=True)))), reverse=True)
    elif sort_by == 'alphabet':
        profiles = profiles.order_by('name')
    elif sort_by == 'random':
        profiles = list(profiles)
        random.shuffle(profiles)
    
    users_data = []
    for profile in profiles:
        user_interests = set(profile.interests.values_list('name', flat=True))
        common_interests = current_user_interests.intersection(user_interests)
        users_data.append({
            'user': profile.user,
            'profile': profile,
            'common_interests': len(common_interests),
            'age': profile.age,  
        })
    
    all_interests = list(Interest.objects.values_list('name', flat=True))
    all_interests_json = json.dumps(all_interests)
    
    context = {
        'users_data': users_data,
        'current_user_city': city_filter,
        'interest_filters': interest_filters,
        'all_interests_json': all_interests_json,
        'current_user_age': current_profile.age,  
        'age_range': age_range, 
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
    interests = profile.interests.all() 
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
    user = request.user 

    if request.method == 'POST':
        profile.name = request.POST.get('name', profile.name)
        profile.age = request.POST.get('age', profile.age)
        profile.bio = request.POST.get('bio', profile.bio)
        
        city_name = request.POST.get('location')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        if city_name:
            city, created = City.objects.get_or_create(
                name=city_name,
                defaults={'latitude': float(latitude) if latitude else None, 'longitude': float(longitude) if longitude else None}
            )
            profile.location = city
        else:
            profile.location = None
            
        profile.status = request.POST.get('status', profile.status)
        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']
        
        new_username = request.POST.get('username', user.username)
        if new_username != user.username:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                messages.error(request, "Этот username уже занят. Выберите другой.")
                return redirect('edit-profile')
            user.username = new_username

        existing_interests = set(profile.interests.values_list('name', flat=True))
        new_interests = request.POST.getlist('interests')
        for interest_name in new_interests:
            interest_name = interest_name.strip()
            if interest_name and interest_name not in existing_interests:
                interest, created = Interest.objects.get_or_create(name=interest_name)
                profile.interests.add(interest)

        user.save()  
        profile.save()  
        messages.success(request, "Профиль успешно обновлен!")
        return redirect('profile-detail', user_id=request.user.id)

    context = {'profile': profile, 'user': user}
    return render(request, 'profiles/edit_profile.html', context)

@login_required
def chat(request, user_id):
    other_user = User.objects.get(id=user_id)
    current_user = request.user
    match = Match.objects.filter(user1=current_user, user2=other_user).first() or \
            Match.objects.filter(user1=other_user, user2=current_user).first()
    
    if not match:
        context = {'other_user': other_user, 'messages': [], 'match': None}
    else:
        messages_qs = Message.objects.filter(match=match).select_related('sender', 'sender__profile').order_by('created_at')
        messages = [{
            'message': msg.content,
            'sender': msg.sender, 
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        } for msg in messages_qs]
        cache_key = f"chat_messages:chat_{min(current_user.id, other_user.id)}_{max(current_user.id, other_user.id)}"
        cache.set(cache_key, messages, timeout=3600)
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

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_recommendations(request):
    current_profile = UserProfile.objects.get(user=request.user)
    current_user_interests = set(current_profile.interests.values_list('name', flat=True))
    
    profiles = UserProfile.objects.exclude(user=request.user).select_related('user', 'location')
    if current_profile.location:
        profiles = profiles.filter(location=current_profile.location)
    
    profiles_list = []
    for profile in profiles:
        user_interests = set(profile.interests.values_list('name', flat=True))
        common_interests = current_user_interests.intersection(user_interests)
        profiles_list.append({
            'user': profile.user,
            'profile': profile,
            'common_interests': len(common_interests),
            'age': profile.age,  
        })
    profiles_list.sort(key=lambda x: x['common_interests'], reverse=True)
    
    current_index = int(request.GET.get('index', 0))
    total_profiles = len(profiles_list)
    
    if total_profiles == 0:
        return render(request, 'profiles/recommendations.html', {'profile_data': None, 'current_index': 0, 'total_profiles': 0})
    
    if current_index < 0:
        current_index = 0
    elif current_index >= total_profiles:
        current_index = total_profiles - 1
    
    profile_data = profiles_list[current_index] if total_profiles > 0 else None
    
    context = {
        'profile_data': profile_data,
        'current_index': current_index,
        'total_profiles': total_profiles,
    }
    return render(request, 'profiles/recommendations.html', context)

@login_required
def all_chats(request):
    current_user = request.user
    matches = Match.objects.filter(user1=current_user) | Match.objects.filter(user2=current_user)
    
    chats = []
    for match in matches:
        other_user = match.user2 if match.user1 == current_user else match.user1
        last_message = Message.objects.filter(match=match).order_by('-created_at').first()
        chats.append({
            'user': other_user,
            'last_message': last_message.content if last_message else "Нет сообщений",
            'last_message_time': last_message.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_message else None,
            'url': f'/main/chat/{other_user.id}/'
        })

    context = {'chats': chats}
    return render(request, 'profiles/all_chats.html', context)