from django.urls import path
from core import views
from django.contrib.auth import views as auth_views
 

urlpatterns=[
    path('',views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('send-request/<int:user_id>/', views.send_request, name='send_request'),
    path('requests/', views.requests_view, name='requests'),
    path('accept/<int:req_id>/', views.accept_request, name='accept_request'),
    path('reject/<int:req_id>/', views.reject_request, name='reject_request'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('search/', views.search_view, name='search'),
    path('chats/', views.chats_list_view, name='chat_list'),
    path('chats/<int:user_id>/', views.chat_view, name='chat'),
    path('chats/<int:user_id>/send/', views.send_message_ajax, name='send_message_ajax'),
    path('chats/<int:user_id>/get/<int:last_msg_id>/', views.get_messages_ajax, name='get_messages_ajax'),
    path('schedule/create/<int:user_id>/', views.create_schedule, name='create_schedule'),
    path('schedules/', views.schedules_list, name='schedules_list'),
    path('schedule/accept/<int:schedule_id>/', views.accept_schedule, name='accept_schedule'),
    path('schedule/reject/<int:schedule_id>/', views.reject_schedule, name='reject_schedule'),

    # Password Reset URLs
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
