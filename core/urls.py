from django.urls import path
from core import views
from django.contrib.auth import views as auth_views
 

urlpatterns=[
    path('',views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('profile/', views.profile_view, name='profile'),
    path('send-request/<int:user_id>/', views.send_request, name='send_request'),
    path('requests/', views.requests_view, name='requests'),
    path('accept/<int:req_id>/', views.accept_request, name='accept_request'),
    path('reject/<int:req_id>/', views.reject_request, name='reject_request'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('search/', views.search_view, name='search'),
    path('chats/', views.chats_list_view, name='chat_list'),
    path('chats/<int:user_id>/', views.chat_view, name='chat'),
    path('chats/<int:user_id>/send/', views.send_message_ajax, name='send_message_ajax'),
    path('chats/<int:user_id>/get/<int:last_msg_id>/', views.get_messages_ajax, name='get_messages_ajax'),
    path('chats/unread-global/', views.get_unread_global_ajax, name='get_unread_global_ajax'),
    
    path('video/<str:room_name>/', views.video_room, name='video_room'),
    
    path('schedule/create/<int:user_id>/', views.create_schedule, name='create_schedule'),
    path('schedules/', views.schedules_list, name='schedules_list'),
    path('schedule/accept/<int:schedule_id>/', views.accept_schedule, name='accept_schedule'),
    path('schedule/reject/<int:schedule_id>/', views.reject_schedule, name='reject_schedule'),
    path('session/<int:session_id>/complete/', views.mark_session_complete, name='mark_session_complete'),
    path('session/<int:session_id>/rate/', views.rate_session, name='rate_session'),

    # Password Reset URLs
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Trust & Safety
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('report/<int:user_id>/', views.report_user, name='report_user'),

    # Admin Analytics
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('ban/<int:user_id>/', views.ban_user, name='ban_user'),
]
