from django.contrib import admin
from core.models import Profile, SwapRequest, Message, Schedule, Rating, Notification


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'skill_level', 'learning_mode',
        'availability', 'location',
        'sessions_completed', 'total_rating', 'rating_count'
    )
    list_editable = ('skill_level', 'learning_mode', 'sessions_completed')
    search_fields = ('user__username', 'user__email', 'location', 'teach_skills', 'learn_skills')
    list_filter = ('skill_level', 'learning_mode', 'availability')


@admin.register(SwapRequest)
class SwapRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'skill_offered', 'skill_wanted', 'status')
    list_filter = ('status',)
    search_fields = ('sender__username', 'receiver__username', 'skill_offered', 'skill_wanted')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    ordering = ('-timestamp',)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'teacher', 'learner', 'start_time', 'status', 'created_at')
    list_filter = ('status', 'start_time')
    search_fields = ('sender__username', 'receiver__username', 'teacher__username', 'learner__username')
    ordering = ('-created_at',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('learner', 'teacher', 'session', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('learner__username', 'teacher__username')
    ordering = ('-created_at',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    ordering = ('-created_at',)
