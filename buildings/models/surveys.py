from django.db import models
from django.forms import ModelForm, widgets
from django.utils.translation import gettext_lazy as _

from buildings.widgets import MyRadioSelect, NumberOrUnsure, CheckboxRequiredSelectMultiple


CHOICES_YES_NO = [
    ("yes", "Yes"),
    ("no", "No"),
]
CHOICES_YES_NO_UNSURE = [
    ("yes", "Yes"),
    ("no", "No"),
    ("unsure", "Unsure"),
]
SITE_OBSTRUCTIONS = [
    ("tress_or_landscaping", "Important trees or landscaping"),
    ("buildings", "Buildings"),
    ("overhead_wires", "Overhead wires, including those blocking general access to site"),
    ("no_obstructions", "No significant obstructions"),
]



class SurveyV1(models.Model):
    has_simple_footprint = models.BooleanField()
    has_simple_volume = models.BooleanField()
    num_storeys = models.IntegerField(blank=True, null=True)
    has_basement = models.BooleanField(blank=True, null=True)
    site_obstructions = models.JSONField()


class SurveyV1Form(ModelForm):
    template_name = "surveys/survey_v1.html"

    class Meta:
        model = SurveyV1
        fields = ["has_simple_footprint", "has_simple_volume", "num_storeys", "has_basement", "site_obstructions"]
        widgets = {
            "has_simple_footprint": MyRadioSelect(choices=CHOICES_YES_NO, attrs={"class": "survey-1col"}),
            "has_simple_volume": MyRadioSelect(choices=CHOICES_YES_NO, attrs={"class": "survey-1col"}),
            "num_storeys": NumberOrUnsure(attrs={"class": "survey-1col"}),
            "has_basement": MyRadioSelect(choices=CHOICES_YES_NO_UNSURE, attrs={"class": "survey-1col"}),
            "site_obstructions": CheckboxRequiredSelectMultiple(choices=SITE_OBSTRUCTIONS, attrs={"class": "survey-1col"})
        }
        labels = {
            "has_simple_footprint": _("Q1"),
            "has_simple_volume": _("Q2"),
            "num_storeys": _("Q3"),
            "has_basement": _("Q4"),
            "site_obstructions": _("Q5"),
        }
        help_texts = {
            "has_simple_footprint": _("Does the building have a simple footprint?"),
            "has_simple_volume": _("Does the building have a simple volumetric form?"),
            "num_storeys": _("How many storeys above-ground does the building have?"),
            "has_basement": _("Does the building have a basement?"),
            "site_obstructions": _("Are there obstructions to machine access around the building (within 3m or less)? Select all that apply.")
        }

