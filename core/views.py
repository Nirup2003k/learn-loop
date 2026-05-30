from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
import json
import re
from django.db.models import Count
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from core.models import Profile, SwapRequest, Message, Schedule, Rating, Notification, Block, Report


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
        swap_related_user_ids = get_swap_related_user_ids(request.user)
        
        return render(request, 'home.html', {
            'matches_count': len(matches),
            'pending_requests_count': received_requests.count(),
            'messages_count': total_messages,
            'sessions_count': total_sessions,
            'top_matches': matches[:2],
            'recent_messages': recent_messages,
            'recent_requests': recent_requests,
            'swap_related_user_ids': swap_related_user_ids,
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
        
        token = get_random_string(32)
        request.session['verification_token'] = token
        request.session['verification_user_id'] = user.id
        
        verification_link = request.build_absolute_uri(f'/verify-email/{token}/')
        send_mail(
            'Verify your LearnLoop Account',
            f'Please click here to verify your account: {verification_link}',
            'noreply@learnloop.com',
            [email],
            fail_silently=False,
        )

        messages.success(request, 'Account created successfully! Please check your email to verify your account.')
        return redirect('/login/')

    return render(request, 'register.html')

def verify_email(request, token):
    stored_token = request.session.get('verification_token')
    user_id = request.session.get('verification_user_id')
    
    if token == stored_token and user_id:
        user = User.objects.get(id=user_id)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.is_email_verified = True
        profile.save()
        messages.success(request, 'Email verified successfully! You can now use all features.')
        
        del request.session['verification_token']
        del request.session['verification_user_id']
    else:
        messages.error(request, 'Invalid or expired verification link.')
        
    return redirect('/login/')






@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.teach_skills = request.POST.get('teach', profile.teach_skills)
        profile.learn_skills = request.POST.get('learn', profile.learn_skills)
        
        # Save the new fields from the POST request
        profile.bio = request.POST.get('bio', profile.bio)
        profile.timezone = request.POST.get('timezone', profile.timezone)
        profile.skill_level = request.POST.get('skill_level', profile.skill_level)
        profile.availability = request.POST.get('availability', profile.availability)
        profile.learning_mode = request.POST.get('learning_mode', profile.learning_mode)
        profile.location = request.POST.get('location', profile.location)
 
        if request.FILES.get('image'):
          profile.image = request.FILES['image']

        profile.save()

    matches = find_matches(profile)

    import zoneinfo
    timezones = sorted(zoneinfo.available_timezones())

    return render(request, 'profile.html', {
        'profile': profile,
        'matches': matches,
        'timezones': timezones
    })




def get_blocked_user_ids(user):
    blocked_by_me = Block.objects.filter(blocker=user).values_list('blocked_user_id', flat=True)
    blocked_me = Block.objects.filter(blocked_user=user).values_list('blocker_id', flat=True)
    return list(blocked_by_me) + list(blocked_me)

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

def get_swap_related_user_ids(user):
    related_user_ids = []
    requests = SwapRequest.objects.filter(Q(sender=user) | Q(receiver=user))
    for req in requests:
        if req.sender == user:
            related_user_ids.append(req.receiver.id)
        else:
            related_user_ids.append(req.sender.id)
    return related_user_ids

def are_users_accepted(user, other_user):
    return SwapRequest.objects.filter(
        Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user),
        status='accepted'
    ).exists()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def create_notification(user, message):
    Notification.objects.get_or_create(
        user=user,
        message=message,
        is_read=False
    )
    
    # Broadcast to WebSocket
    channel_layer = get_channel_layer()
    room_group_name = f"user_{user.id}_notifications"
    
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'send_notification',
            'message': message
        }
    )

def find_matches(current_profile):
    matches_with_scores = []

    # Clean and lowercase skills, ignoring empty strings
    my_teach = [skill.strip().lower() for skill in current_profile.teach_skills.split(',') if skill.strip()]
    my_learn = [skill.strip().lower() for skill in current_profile.learn_skills.split(',') if skill.strip()]

    accepted_user_ids = get_accepted_user_ids(current_profile.user)
    blocked_user_ids = get_blocked_user_ids(current_profile.user)
    highly_reported_users = User.objects.annotate(rc=Count('reports_received')).filter(rc__gte=3).values_list('id', flat=True)

    all_profiles = Profile.objects.exclude(user=current_profile.user).exclude(user_id__in=accepted_user_ids).exclude(user_id__in=blocked_user_ids).exclude(user_id__in=highly_reported_users)

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
            
            # Reputation System Additions
            if profile.rating_count > 0:
                score += (profile.average_rating * 2)
            score += (profile.sessions_completed * 0.5)

        if score > 0:
            matches_with_scores.append((profile, score))

    # Sort results by score (highest first)
    matches_with_scores.sort(key=lambda x: x[1], reverse=True)

    return matches_with_scores




# send request
@login_required
def send_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    
    if receiver == request.user:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Cannot send request to yourself'}, status=400)
        return redirect('/dashboard/')

    # Prevent duplicate requests after any previous swap relationship in either direction.
    existing_request = SwapRequest.objects.filter(
        (Q(sender=request.user, receiver=receiver) | Q(sender=receiver, receiver=request.user)),
    ).exists()
    
    if existing_request:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Request already exists'}, status=400)
        return redirect('/dashboard/')

    sender_profile = Profile.objects.get(user=request.user)

    # simple logic (first skill only for now)
    skill_offered = sender_profile.teach_skills.split(',')[0] if sender_profile.teach_skills else ''
    skill_wanted = sender_profile.learn_skills.split(',')[0] if sender_profile.learn_skills else ''

    swap_request = SwapRequest.objects.create(
        sender=request.user,
        receiver=receiver,
        skill_offered=skill_offered,
        skill_wanted=skill_wanted
    )
    create_notification(
        receiver,
        f"{request.user.username} sent you a swap request."
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Request sent'})
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
        req = get_object_or_404(SwapRequest, id=req_id, receiver=request.user, status='pending')
        req.status = 'accepted'
        req.save()
        create_notification(
            req.sender,
            f"{request.user.username} accepted your swap request."
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Request accepted'})
    return redirect('requests')

@login_required
def reject_request(request, req_id):
    if request.method == "POST":
        req = get_object_or_404(SwapRequest, id=req_id, receiver=request.user, status='pending')
        req.status = 'rejected'
        req.save()
        create_notification(
            req.sender,
            f"{request.user.username} rejected your swap request."
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Request rejected'})
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
    swap_related_user_ids = get_swap_related_user_ids(request.user)
    
    total_messages = Message.objects.filter(receiver=request.user).count()
    
    from django.utils import timezone
    import zoneinfo
    from datetime import datetime
    
    now = timezone.now()
    current_date = now.date()
    current_time = now.time()

    # Get user's upcoming schedules (status 'accepted' and in the future)
    upcoming_sessions = Schedule.objects.filter(
        Q(teacher=request.user) | Q(learner=request.user),
        status='accepted',
        start_time__gte=now
    ).order_by('start_time')
    
    # Get user's completed schedules
    completed_sessions = Schedule.objects.filter(
        Q(teacher=request.user) | Q(learner=request.user),
        status='completed'
    ).order_by('-start_time')
    
    # Calculate completed sessions from Profile
    total_sessions = profile.sessions_completed
    
    # Get top users based on reputation
    all_rated_profiles = list(Profile.objects.filter(rating_count__gt=0).exclude(user=request.user))
    top_users = sorted(all_rated_profiles, key=lambda p: (p.average_rating, p.sessions_completed), reverse=True)[:5]
    
    latest_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'dashboard.html', {
        'profile': profile,
        'matches': matches[:3],  # limit to 3
        'total_matches': len(matches),
        'received': received_requests,
        'sent': sent_requests,
        'sent_ids': sent_ids,
        'swap_related_user_ids': swap_related_user_ids,
        'total_messages': total_messages,
        'total_sessions': total_sessions,
        'upcoming_sessions': upcoming_sessions,
        'completed_sessions': completed_sessions,
        'top_users': top_users,
        'latest_notifications': latest_notifications,
        'unread_notifications_count': unread_notifications_count
    })

@login_required
def mark_notification_read(request, notification_id):
    if request.method == "POST":
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
    return redirect(request.POST.get('next') or 'dashboard')

@login_required
def mark_all_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.POST.get('next') or 'notifications')

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications_count = notifications.filter(is_read=False).count()
    read_notifications_count = notifications.filter(is_read=True).count()

    return render(request, 'notifications.html', {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'read_notifications_count': read_notifications_count,
    })
    
def search_view(request):
    query = request.GET.get('q')

    results = []

    if query:
        highly_reported_users = User.objects.annotate(rc=Count('reports_received')).filter(rc__gte=3).values_list('id', flat=True)
        results = Profile.objects.exclude(user_id__in=highly_reported_users).filter(
            Q(teach_skills__icontains=query) | Q(learn_skills__icontains=query)
        )

    swap_related_user_ids = []
    if request.user.is_authenticated:
        swap_related_user_ids = get_swap_related_user_ids(request.user)

    return render(request, 'search.html', {
        'results': results,
        'query': query,
        'swap_related_user_ids': swap_related_user_ids
    })


                                    #create chat view

                                    # Chat with a specific user
@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if not are_users_accepted(request.user, other_user):
        messages.error(request, "You can only chat with accepted skill-swap partners.")
        return redirect('requests')

    # Get messages (both directions)
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')
    messages.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

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
        if not are_users_accepted(request.user, other_user):
            return JsonResponse({'status': 'error', 'message': 'Chat is only available between accepted users.'}, status=403)
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
    if not are_users_accepted(request.user, other_user):
        return JsonResponse({'status': 'error', 'message': 'Chat is only available between accepted users.'}, status=403)
    
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user),
        id__gt=last_msg_id
    ).order_by('timestamp')
    messages.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    msgs_data = []
    for msg in messages:
        msgs_data.append({
            'id': msg.id,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime("%H:%M"),
            'sender_id': msg.sender.id
        })

    return JsonResponse({'status': 'success', 'messages': msgs_data})

@login_required
def get_unread_global_ajax(request):
    try:
        last_id = int(request.GET.get('last_id', 0))
    except ValueError:
        last_id = 0
        
    unread = Message.objects.filter(
        receiver=request.user,
        is_read=False,
        id__gt=last_id
    ).order_by('timestamp')
    
    data = []
    for msg in unread:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'content': msg.content,
            'sender_id': msg.sender.id
        })
        
    return JsonResponse({'status': 'success', 'messages': data})


# Chat list (all users you talked with)
@login_required
def chats_list_view(request):
    accepted_user_ids = get_accepted_user_ids(request.user)
    blocked_user_ids = get_blocked_user_ids(request.user)
    accepted_users = User.objects.filter(id__in=accepted_user_ids).exclude(id__in=blocked_user_ids).order_by('username')

    chat_partners = []
    for user in accepted_users:
        last_message = Message.objects.filter(
            Q(sender=request.user, receiver=user) |
            Q(sender=user, receiver=request.user)
        ).order_by('-timestamp').first()

        chat_partners.append({
            'user': user,
            'last_message': last_message,
            'unread_count': Message.objects.filter(
                sender=user,
                receiver=request.user,
                is_read=False
            ).count(),
        })

    return render(request, 'chat_list.html', {
        'chat_partners': chat_partners
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

        skill = request.POST.get('skill', '').strip()
        if not skill:
            messages.error(request, "Skill cannot be empty.")
            return render(request, 'create_schedule.html', {'receiver': receiver})

        sender_profile = Profile.objects.get(user=request.user)
        receiver_profile = Profile.objects.get(user=receiver)

        their_teach_skills = [s.strip().lower() for s in receiver_profile.teach_skills.split(',') if s.strip()]
        my_teach_skills = [s.strip().lower() for s in sender_profile.teach_skills.split(',') if s.strip()]

        skill_lower = skill.lower()

        # Role Assignment
        if any(skill_lower in s for s in their_teach_skills) or any(s in skill_lower for s in their_teach_skills):
            teacher = receiver
            learner = request.user
        elif any(skill_lower in s for s in my_teach_skills) or any(s in skill_lower for s in my_teach_skills):
            teacher = request.user
            learner = receiver
        else:
            messages.error(request, f"'{skill}' does not match any teachable skills.")
            return render(request, 'create_schedule.html', {'receiver': receiver})

        try:
            # Combine into naive datetime
            naive_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            # Make it timezone aware based on user's local timezone
            user_tz = zoneinfo.ZoneInfo(request.user.profile.timezone)
            start_time = naive_dt.replace(tzinfo=user_tz)

            schedule = Schedule.objects.create(
                sender=request.user,
                receiver=receiver,
                teacher=teacher,
                learner=learner,
                skill=skill,
                start_time=start_time,
                meeting_link=meeting_link
            )
            create_notification(
                receiver,
                f"{request.user.username} scheduled a session for {skill}."
            )
            return redirect('schedules_list')
        except Exception as e:
            messages.error(request, str(e))
            return render(request, 'create_schedule.html', {'receiver': receiver})

    return render(request, 'create_schedule.html', {'receiver': receiver})

@login_required
def schedules_list(request):
    active_statuses = ['pending', 'accepted']
    received = Schedule.objects.filter(receiver=request.user, status__in=active_statuses).order_by('start_time')
    sent = Schedule.objects.filter(sender=request.user, status__in=active_statuses).order_by('start_time')

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

from django.utils import timezone
import zoneinfo
from datetime import datetime

@login_required
def mark_session_complete(request, session_id):
    if request.method == "POST":
        schedule = get_object_or_404(Schedule, id=session_id)
        
        if schedule.status != 'accepted':
            messages.error(request, "You can only complete sessions that have been accepted.")
            return redirect('dashboard')
            
        # Ensure user is part of session
        if request.user != schedule.teacher and request.user != schedule.learner:
            return redirect('dashboard')
            
        if request.user == schedule.teacher:
            schedule.teacher_completed = True
            schedule.teacher_completed_at = timezone.now()
        else:
            schedule.learner_completed = True
            schedule.learner_completed_at = timezone.now()
            
        schedule.save()
        
        # Check if both completed
        if schedule.teacher_completed and schedule.learner_completed and schedule.status != 'completed':
            schedule.status = 'completed'
            schedule.save()
            
            # Update profiles
            p1 = Profile.objects.get(user=schedule.teacher)
            p1.sessions_completed += 1
            p1.save()
            
            p2 = Profile.objects.get(user=schedule.learner)
            p2.sessions_completed += 1
            p2.save()
            
            create_notification(
                schedule.teacher,
                f"Your session for {schedule.skill} has been marked completed."
            )
            create_notification(
                schedule.learner,
                f"Your session for {schedule.skill} has been marked completed."
            )
            
            messages.success(request, "Session marked as completed!")
        else:
            messages.success(request, "You marked this session as completed. Waiting for the other user.")
            
    return redirect('dashboard')


@login_required
def rate_session(request, session_id):
    if request.method == "POST":
        schedule = get_object_or_404(Schedule, id=session_id)
        
        # Only learner can rate
        if request.user != schedule.learner:
            messages.error(request, "Only the learner can rate the session.")
            return redirect('dashboard')
            
        # Ensure session is completed
        if schedule.status != 'completed':
            messages.error(request, "You can only rate completed sessions.")
            return redirect('dashboard')
            
        # Prevent duplicate ratings
        if Rating.objects.filter(session=schedule).exists():
            messages.error(request, "You have already rated this session.")
            return redirect('dashboard')
            
        rating_val = int(request.POST.get('rating', 0))
        review_text = request.POST.get('review', '').strip()
        
        if 1 <= rating_val <= 5:
            Rating.objects.create(
                session=schedule,
                teacher=schedule.teacher,
                learner=schedule.learner,
                rating=rating_val,
                feedback=review_text
            )
            
            # Recalculate average rating for the teacher
            profile = Profile.objects.get(user=schedule.teacher)
            profile.total_rating += rating_val
            profile.rating_count += 1
            profile.save()
            
            messages.success(request, f"You rated {schedule.teacher.username} {rating_val} stars!")
        else:
            messages.error(request, "Invalid rating value.")
            
    return redirect('dashboard')

@login_required
def video_room(request, room_name):
    # Security: Ensure user is authenticated to enter a video room
    return render(request, 'video_room.html', {
        'room_name': room_name
    })

@login_required
def block_user(request, user_id):
    if request.method == "POST":
        blocked_user = get_object_or_404(User, id=user_id)
        if blocked_user != request.user:
            Block.objects.get_or_create(blocker=request.user, blocked_user=blocked_user)
            messages.success(request, f"You have blocked {blocked_user.username}.")
    return redirect('home')

@login_required
def report_user(request, user_id):
    if request.method == "POST":
        reported_user = get_object_or_404(User, id=user_id)
        reason = request.POST.get('reason', '').strip()
        if reported_user != request.user and reason:
            Report.objects.create(
                reporter=request.user,
                reported_user=reported_user,
                reason=reason
            )
            messages.success(request, f"You have reported {reported_user.username}. Our team will review this.")
    return redirect('home')

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_dashboard(request):
    total_users = User.objects.count()
    total_sessions = Schedule.objects.filter(status='completed').count()
    pending_reports = Report.objects.filter(is_resolved=False).order_by('-created_at')
    
    # Calculate top skills
    from django.db.models import Count
    top_skills = SwapRequest.objects.values('skill_wanted').annotate(count=Count('skill_wanted')).order_by('-count')[:5]

    return render(request, 'admin_dashboard.html', {
        'total_users': total_users,
        'total_sessions': total_sessions,
        'pending_reports': pending_reports,
        'top_skills': top_skills
    })



@staff_member_required
def ban_user(request, user_id):
    if request.method == 'POST':
        user_to_ban = get_object_or_404(User, id=user_id)
        if not user_to_ban.is_superuser:
            user_to_ban.is_active = False
            user_to_ban.save()
            # Resolve all reports for this user
            Report.objects.filter(reported_user=user_to_ban).update(is_resolved=True)
            messages.success(request, f'User {user_to_ban.username} has been permanently banned.')
        else:
            messages.error(request, 'Cannot ban a superuser.')
    return redirect('admin_dashboard')
