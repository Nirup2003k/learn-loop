from django.contrib import admin
from core.models import Profile, SwapRequest, Message, Schedule


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'skill_level', 'learning_mode',
        'availability', 'location',
        'sessions_completed', 'rating'
    )
    list_editable = ('skill_level', 'learning_mode', 'sessions_completed', 'rating')
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
    list_display = ('sender', 'receiver', 'date', 'time', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('sender__username', 'receiver__username')
    ordering = ('-created_at',)