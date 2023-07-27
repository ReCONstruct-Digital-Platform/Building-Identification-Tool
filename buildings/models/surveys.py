from django.db import models

CHOICES_YES_NO = [
    ("Yes", "yes"),
    ("No", "no"),
]
CHOICES_YES_NO_UNSURE = [
    ("Yes", "yes"),
    ("No", "no"),
    ("Unsure", "unsure"),
]

class SurveyV1(models.Model):
    q1 = models.CharField(max_length=3, choices=CHOICES_YES_NO)
    q2 = models.CharField(max_length=3, choices=CHOICES_YES_NO)
    q3 = models.CharField(max_length=3, choices=CHOICES_YES_NO)
    q4 = models.CharField(max_length=6, choices=CHOICES_YES_NO_UNSURE)

