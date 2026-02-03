from django import template

register = template.Library()

@register.filter
def div_to_percent(value, arg):
    try:
        val = float(value)
        total = float(arg)
        if total <= 0:
            return 0
        return min((val / total) * 100, 100)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
