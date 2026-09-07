from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Grade, Institute


DEFAULT_GRADES = (
    ('A+', 90, 100, 1),
    ('A', 80, 89.99, 2),
    ('B', 70, 79.99, 3),
    ('C', 60, 69.99, 4),
    ('D', 50, 59.99, 5),
    ('E', 0, 49.99, 6),
)


@receiver(post_save, sender=Institute)
def create_default_grades(sender, instance, created, **kwargs):
    if not created:
        return

    Grade.objects.bulk_create([
        Grade(
            institute=instance,
            grade=grade,
            min_percentage=minimum,
            max_percentage=maximum,
            order=order,
        )
        for grade, minimum, maximum, order in DEFAULT_GRADES
    ])
