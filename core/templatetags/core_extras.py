from django import template
from core.models import Rating

register = template.Library()

@register.simple_tag
def has_rated(session, user):
    return Rating.objects.filter(session=session, learner=user).exists()
