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
    teach_skills = models.TextField(blank=True, default='')
    learn_skills = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='profiles/', default='default.png')
    
    is_email_verified = models.BooleanField(default=False)
    
    bio = models.TextField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVEL_CHOICES, default='beginner')
    availability = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., weekends, evenings, flexible")
    learning_mode = models.CharField(max_length=10, choices=LEARNING_MODE_CHOICES, default='both')
    location = models.CharField(max_length=100, blank=True, null=True)
    sessions_completed = models.IntegerField(default=0)
    total_rating = models.IntegerField(default=0)
    rating_count = models.IntegerField(default=0)
    
    @property
    def average_rating(self):
        if self.rating_count > 0:
            return round(self.total_rating / self.rating_count, 1)
        return 0.0

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
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} → {self.receiver}"

class Schedule(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_schedules')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_schedules')
    
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_sessions', null=True)
    learner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_sessions', null=True)
    skill = models.CharField(max_length=100, null=True)
    
    start_time = models.DateTimeField(null=True, blank=True)
    meeting_link = models.URLField(blank=True, null=True)
    
    status = models.CharField(max_length=20, default='pending')
    
    teacher_completed = models.BooleanField(default=False)
    learner_completed = models.BooleanField(default=False)
    teacher_completed_at = models.DateTimeField(null=True, blank=True)
    learner_completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.teacher and self.learner and self.teacher == self.learner:
            raise ValidationError("Teacher and learner cannot be the same user.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session: {self.teacher} teaching {self.learner} ({self.status})"

class Rating(models.Model):
    session = models.OneToOneField(Schedule, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    learner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    rating = models.IntegerField()
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.learner} rated {self.teacher} {self.rating} stars"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"

class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_submitted')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reporter.username} reported {self.reported_user.username}"

class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_created')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked_user')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked_user.username}"
