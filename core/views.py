from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
import json
import re
from core.models import Profile, SwapRequest, Message, Schedule


# Create your views here.

def home(request):
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        matches = find_matches(profile)
        received_requests = SwapRequest.objects.filter(receiver=request.user, status='pending')
        total_messages = Message.objects.filter(receiver=request.user).count()
        total_sessions = Schedule.objects.filter(Q(sender=request.user) | Q(receiver=request.user), status='accepted').count()
        
        recent_messages = Message.objects.filter(receiver=request.user).order_by('-timestamp')[:2]
        recent_requests = received_requests.order_by('-id')[:2]
        
        return render(request, 'home.html', {
            'matches_count': len(matches),
            'pending_requests_count': received_requests.count(),
            'messages_count': total_messages,
            'sessions_count': total_sessions,
            'top_matches': matches[:2],
            'recent_messages': recent_messages,
            'recent_requests': recent_requests,
        })
    return render(request, 'home.html')
    

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request,  username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/dashboard/')

        else:
            return render(request, 'login.html',{'error': 'Invalid credentials'})
        
    return render(request, 'login.html')




def register_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST.get('email', '').strip()
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if not email:
            return render(request, 'register.html', {'error': 'Email address is required'})

        # Check passwords match
        if password != confirm_password:
            return render(request, 'register.html', {'error': 'Passwords do not match'})

        # Check username exists
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already taken'})

        # Check if email is already in use
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email is already registered'})

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, 'Account created successfully! Please log in.')

        return redirect('/login/')

    return render(request, 'register.html')






@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.teach_skills = request.POST.get('teach', profile.teach_skills)
        profile.learn_skills = request.POST.get('learn', profile.learn_skills)
        
        # Save the new fields from the POST request
        profile.bio = request.POST.get('bio', profile.bio)
        profile.skill_level = request.POST.get('skill_level', profile.skill_level)
        profile.availability = request.POST.get('availability', profile.availability)
        profile.learning_mode = request.POST.get('learning_mode', profile.learning_mode)
        profile.location = request.POST.get('location', profile.location)
 
        if request.FILES.get('image'):
          profile.image = request.FILES['image']

        profile.save()

    matches = find_matches(profile)

    return render(request, 'profile.html', {
        'profile': profile,
        'matches': matches
    })



def get_accepted_user_ids(user):
    accepted_user_ids = []
    accepted_requests = SwapRequest.objects.filter(
        Q(sender=user) | Q(receiver=user),
        status='accepted'
    )
    for req in accepted_requests:
        if req.sender == user:
            accepted_user_ids.append(req.receiver.id)
        else:
            accepted_user_ids.append(req.sender.id)
    return accepted_user_ids

def find_matches(current_profile):
    matches_with_scores = []

    # Clean and lowercase skills, ignoring empty strings
    my_teach = [skill.strip().lower() for skill in current_profile.teach_skills.split(',') if skill.strip()]
    my_learn = [skill.strip().lower() for skill in current_profile.learn_skills.split(',') if skill.strip()]

    accepted_user_ids = get_accepted_user_ids(current_profile.user)

    all_profiles = Profile.objects.exclude(user=current_profile.user).exclude(user_id__in=accepted_user_ids)

    for profile in all_profiles:
        their_teach = [skill.strip().lower() for skill in profile.teach_skills.split(',') if skill.strip()]
        their_learn = [skill.strip().lower() for skill in profile.learn_skills.split(',') if skill.strip()]

        score = 0

        # A. Skill Match: my teach matches their learn -> +5 points
        teach_match = False
        for t_skill in my_teach:
            for l_skill in their_learn:
                # Use word boundaries for precise partial match (e.g., "python" inside "python basics")
                if re.search(rf'\b{re.escape(t_skill)}\b', l_skill) or re.search(rf'\b{re.escape(l_skill)}\b', t_skill):
                    score += 5
                    teach_match = True
                    break
            if teach_match:
                break

        # B. Reverse Match: my learn matches their teach -> +5 points
        learn_match = False
        for l_skill in my_learn:
            for t_skill in their_teach:
                if re.search(rf'\b{re.escape(l_skill)}\b', t_skill) or re.search(rf'\b{re.escape(t_skill)}\b', l_skill):
                    score += 5
                    learn_match = True
                    break
            if learn_match:
                break

        # Secondary Factors (Only applied if there's at least one Primary match)
        if teach_match or learn_match:
            # D. Skill Level Compatibility
            if current_profile.skill_level and profile.skill_level:
                if current_profile.skill_level != profile.skill_level:
                    score += 2 # Different levels complement each other
                else:
                    score += 1 # Same level

            # E. Availability Match
            if current_profile.availability and profile.availability:
                my_avail = current_profile.availability.strip().lower()
                their_avail = profile.availability.strip().lower()
                if my_avail and their_avail and my_avail == their_avail:
                    score += 2

            # F. Location Match
            if current_profile.location and profile.location:
                my_loc = current_profile.location.strip().lower()
                their_loc = profile.location.strip().lower()
                if my_loc and their_loc and my_loc == their_loc:
                    score += 1

        if score > 0:
            matches_with_scores.append((profile, score))

    # Sort results by score (highest first)
    matches_with_scores.sort(key=lambda x: x[1], reverse=True)

    return matches_with_scores




# send request
@login_required
def send_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    
    # Check if a request already exists between these users that is accepted
    existing_accepted = SwapRequest.objects.filter(
        (Q(sender=request.user, receiver=receiver) | Q(sender=receiver, receiver=request.user)),
        status='accepted'
    ).exists()
    
    if existing_accepted:
        return redirect('/dashboard/')

    # Check if a pending request already exists for (sender=request.user, receiver=user_id)
    existing_pending = SwapRequest.objects.filter(
        sender=request.user, receiver=receiver, status='pending'
    ).exists()
    
    if existing_pending:
        return redirect('/dashboard/')

    sender_profile = Profile.objects.get(user=request.user)

    # simple logic (first skill only for now)
    skill_offered = sender_profile.teach_skills.split(',')[0] if sender_profile.teach_skills else ''
    skill_wanted = sender_profile.learn_skills.split(',')[0] if sender_profile.learn_skills else ''

    SwapRequest.objects.create(
        sender=request.user,
        receiver=receiver,
        skill_offered=skill_offered,
        skill_wanted=skill_wanted
    )

    return redirect('/profile/')

@login_required
def requests_view(request):
    received = SwapRequest.objects.filter(receiver=request.user)
    sent = SwapRequest.objects.filter(sender=request.user)

    return render(request, 'requests.html', {
        'received': received,
        'sent': sent
    })

@login_required
def accept_request(request, req_id):
    if request.method == "POST":
        req = SwapRequest.objects.get(id=req_id)
        req.status = 'accepted'
        req.save()
    return redirect('requests')

@login_required
def reject_request(request, req_id):
    if request.method == "POST":
        req = SwapRequest.objects.get(id=req_id)
        req.status = 'rejected'
        req.save()
    return redirect('requests')


     

def logout_view(request):
    logout(request)
    return redirect('/')


#dashboard


@login_required
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    matches = find_matches(profile)

    received_requests = SwapRequest.objects.filter(
        receiver=request.user, status='pending'
    )

    sent_requests = SwapRequest.objects.filter(
        sender=request.user, status='pending'
    )
    
    sent_ids = sent_requests.values_list('receiver_id', flat=True)
    
    total_messages = Message.objects.filter(receiver=request.user).count()
    total_sessions = Schedule.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user), status='accepted'
    ).count()

    return render(request, 'dashboard.html', {
        'profile': profile,
        'matches': matches[:3],  # limit to 3
        'total_matches': len(matches),
        'received': received_requests,
        'sent': sent_requests,
        'sent_ids': sent_ids,
        'total_messages': total_messages,
        'total_sessions': total_sessions
    })
    
def search_view(request):
    query = request.GET.get('q')

    results = []

    if query:
        results = Profile.objects.filter(
            teach_skills__icontains=query
        ) | Profile.objects.filter(
            learn_skills__icontains=query
        )

    accepted_user_ids = []
    if request.user.is_authenticated:
        accepted_user_ids = get_accepted_user_ids(request.user)

    return render(request, 'search.html', {
        'results': results,
        'query': query,
        'accepted_user_ids': accepted_user_ids
    })


                                    #create chat view

                                    # Chat with a specific user
@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    # Get messages (both directions)
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')

    # Send message
    if request.method == "POST":
        content = request.POST.get('message')

        if content and content.strip():
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content.strip()
            )

        return redirect('chat', user_id=user_id)

    return render(request, 'chat.html', {
        'messages': messages,
        'other_user': other_user
    })

@login_required
def send_message_ajax(request, user_id):
    if request.method == "POST":
        other_user = get_object_or_404(User, id=user_id)
        try:
            data = json.loads(request.body)
            content = data.get('message', '').strip()
        except:
            content = request.POST.get('message', '').strip()

        if content:
            msg = Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content
            )
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': msg.id,
                    'content': msg.content,
                    'timestamp': msg.timestamp.strftime("%H:%M"),
                    'sender_id': msg.sender.id
                }
            })
        return JsonResponse({'status': 'error', 'message': 'Empty content'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def get_messages_ajax(request, user_id, last_msg_id):
    other_user = get_object_or_404(User, id=user_id)
    
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user),
        id__gt=last_msg_id
    ).order_by('timestamp')

    msgs_data = []
    for msg in messages:
        msgs_data.append({
            'id': msg.id,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime("%H:%M"),
            'sender_id': msg.sender.id
        })

    return JsonResponse({'status': 'success', 'messages': msgs_data})


# Chat list (all users you talked with)
@login_required
def chats_list_view(request):
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )

    users = set()

    for msg in messages:
        if msg.sender == request.user:
            users.add(msg.receiver)
        else:
            users.add(msg.sender)

    return render(request, 'chat_list.html', {
        'users': users
    })

# --- Scheduling ---

@login_required
def create_schedule(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    
    # Check if they are matched
    existing_accepted = SwapRequest.objects.filter(
        (Q(sender=request.user, receiver=receiver) | Q(sender=receiver, receiver=request.user)),
        status='accepted'
    ).exists()
    
    if not existing_accepted:
        return redirect('/requests/')

    if request.method == "POST":
        date = request.POST.get('date')
        time = request.POST.get('time')
        meeting_link = request.POST.get('meeting_link', '')

        Schedule.objects.create(
            sender=request.user,
            receiver=receiver,
            date=date,
            time=time,
            meeting_link=meeting_link
        )
        return redirect('schedules_list')

    return render(request, 'create_schedule.html', {'receiver': receiver})

@login_required
def schedules_list(request):
    received = Schedule.objects.filter(receiver=request.user).order_by('-date', '-time')
    sent = Schedule.objects.filter(sender=request.user).order_by('-date', '-time')

    return render(request, 'schedules.html', {
        'received': received,
        'sent': sent
    })

@login_required
def accept_schedule(request, schedule_id):
    if request.method == "POST":
        schedule = get_object_or_404(Schedule, id=schedule_id, receiver=request.user)
        schedule.status = 'accepted'
        schedule.save()
    return redirect('schedules_list')

@login_required
def reject_schedule(request, schedule_id):
    if request.method == "POST":
        schedule = get_object_or_404(Schedule, id=schedule_id, receiver=request.user)
        schedule.status = 'rejected'
        schedule.save()
    return redirect('schedules_list')


# Custom Password Reset Views
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from core.forms import CustomPasswordResetForm

class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    template_name = 'password_reset_form.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('login')
    success_message = "We've emailed you instructions for setting your password. You should receive them shortly."

class CustomPasswordResetConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('login')
    success_message = "Password updated successfully! You can now log in."
