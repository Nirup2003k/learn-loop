from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
class Profile(models.Model):
    SKILL_LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ]

    LEARNING_MODE_CHOICES = [
        ('chat', 'Chat'),
        ('video', 'Video'),
        ('both', 'Both'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    teach_skills = models.TextField()
    learn_skills = models.TextField()
    image = models.ImageField(upload_to='profiles/', default='default.png')
    
    bio = models.TextField(blank=True, null=True)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVEL_CHOICES, default='beginner')
    availability = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., weekends, evenings, flexible")
    learning_mode = models.CharField(max_length=10, choices=LEARNING_MODE_CHOICES, default='both')
    location = models.CharField(max_length=100, blank=True, null=True)
    sessions_completed = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class SwapRequest(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')

    skill_offered = models.CharField(max_length=100)
    skill_wanted = models.CharField(max_length=100)

    status = models.CharField(max_length=20, default='pending')


    def __str__(self):
        return f"{self.sender} → {self.receiver} ({self.status})"
    
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')

    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} → {self.receiver}"

class Schedule(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_schedules')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_schedules')
    
    date = models.DateField()
    time = models.TimeField()
    meeting_link = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Meeting: {self.sender} & {self.receiver} on {self.date} at {self.time}"