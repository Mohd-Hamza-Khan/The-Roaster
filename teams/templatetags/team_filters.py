from django import template
from teams.models import Availability

register = template.Library()

@register.filter(name='get_day_display')
def get_day_display(day_code):
    """Convert day code to full name"""
    day_dict = dict(Availability.DAY_CHOICES)
    return day_dict.get(day_code, day_code)