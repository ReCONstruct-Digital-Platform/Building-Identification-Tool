import logging
from pprint import pprint

from django.db import models
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from buildings.models.models import Vote

from buildings.widgets import (
    MultiCheckboxSpecify, RadioSelect, NumberOrUnsure, 
    MultiCheckboxSpecifyRequired, SelfSimilarClusterWidget
)


# The first element is the actual value
# forms will pass it as a string nack to the backend
YES_NO = [
    (True, "Yes"),
    (False, "No"),
]
YES_NO_UNSURE = [
    (True, "Yes"),
    (False, "No"),
    (None, "Unsure"),
]
SITE_OBSTRUCTIONS = [
    ("trees_or_landscaping", "Important trees or landscaping"),
    ("buildings", "Buildings"),
    ("overhead_wires", "Overhead wires, incl. those blocking general access to site"),
]
APPENDAGES = [
    ("canopies_eaves", "Roof overhangs/eaves"),
    ("balconies", "Balconies"),
    ("porches_stoops", "Porches/stoops"),
    ("vestibules", "Exterior Vestibules"),
]
FACADE_MATERIALS = [
    ("brick_masonry", "Brick Masonry"),
    ("concrete", "Concrete"),
    ("curtain_wall", "Curtain Wall"),
    ("plaster", "Plaster"),
    ("metal", "Metal"),
    ("vinyl", "Vinyl"),
    ("stone_masonry", "Stone Masonry"),
    ("wood", "Wood"),
    ("unsure", "Unsure"),
]
ROOF_GEOMETRIES = [
    ("flat", "Flat"),
    ("pitch_low", "Low Pitched"),
    ("pitch_high", "High Pitched"),
    ("curved", "Curved"),
    ("complex", "Complex"),
    ("unsure", "Unsure"),
]

# TODO: We might re-use this question for expert users at a later time
STRUCTURE_TYPES = [
    ("wood_frame_light_gauge_steel", "Wood frame or light gauge steel"),
    ("concrete_frame", "Concrete frame"),
    ("steel_frame", "Steel frame"),
    ("brick_masonry", "Load-bearing brick masonry"),
    ("stone_masonry", "Load-bearing stone masonry"),
    ("unsure", "Unsure"),
]
WINDOWS = [
    ("very_large_windows", "Very large"),
    ("irregular_windows", "Irregularly shaped"),
]
NEW_OR_RENOVATED = [
    ("newly_built", "Newly built"),
    ("recently_renovated", "Recently renovated"),
]


class JSONFieldForSpecify(models.JSONField):
    """Field that holds an array of values, including user specified ones.
    Remove the "on" value that gets inserted when users specify a value
    """
    def to_python(self, value):
        super().to_python(value)
        # Return an empty list if no input was given.
        if "on" in value:
            value.remove("on")
        return value


class BaseSurvey(models.Model):
    """
    Base class for Surveys.
    Can add other fields that will be common to all here.
    """
    vote = models.OneToOneField(Vote, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class SurveyV1(BaseSurvey):
    self_similar_cluster = models.IntegerField(blank=True, null=True)
    has_simple_footprint = models.BooleanField()
    has_simple_volume = models.BooleanField()
    num_storeys = models.IntegerField(blank=True, null=True)
    has_basement = models.BooleanField(blank=True, null=True)
    site_obstructions = JSONFieldForSpecify(blank=True, null=True) # checkbox multiple w specify not required
    appendages = JSONFieldForSpecify(blank=True, null=True) # checkbox multiple w specify not required
    exterior_cladding = JSONFieldForSpecify() # checkbox multiple w specify
    facade_condition = models.BooleanField(blank=True, null=True) # radio
    window_wall_ratio = models.BooleanField(blank=True, null=True) # radio
    large_irregular_windows = models.JSONField(blank=True, null=True) # checkbox multiple not required
    roof_geometry = models.JSONField(blank=True, null=True)
    new_or_renovated = models.JSONField(blank=True, null=True)
    # structure_type = models.TextField() # radio w specify 


 
class SurveyV1Form(ModelForm):
    # Some reading:
    # https://docs.djangoproject.com/en/4.2/ref/forms/api/
    # https://docs.djangoproject.com/en/4.2/topics/forms/modelforms/
    # https://docs.djangoproject.com/en/4.2/ref/forms/widgets/
    # https://docs.djangoproject.com/en/4.2/ref/forms/validation/

    template_name = "buildings/surveys/survey_v1.html"
    json_fields = ['site_obstructions', 'appendages', 'exterior_cladding']
    field_ordering = {
        "self_similar_cluster": 1,
        "has_simple_footprint": 2,
        "has_simple_volume": 3,
        "num_storeys": 4,
        "has_basement": 5,
        "site_obstructions": 6,
        "appendages": 7,
        "exterior_cladding": 8,
        "facade_condition": 9,
        "window_wall_ratio": 10,
        "large_irregular_windows": 11,
        "roof_geometry": 12,
        "new_or_renovated": 13,
    }

    def __init__(self, *data, **kwargs):
        super().__init__(*data, **kwargs)

        self.was_filled = False
        # If a non-null instance was passed, there was a previous survey
        # submission for this building and this user.
        if 'instance' in kwargs and kwargs['instance']:
            self.was_filled = True

            # Add initial values to the widgets
            for field in self.fields:
                self.fields[field].widget.was_filled = self.was_filled
                self.fields[field].widget.initial = self.initial[field]
        

    class Meta:
        model = SurveyV1

        fields = ["self_similar_cluster", "has_simple_footprint", "has_simple_volume", 
                  "num_storeys", "has_basement", "site_obstructions", "appendages", 
                  "exterior_cladding", "facade_condition", "window_wall_ratio", 
                  "large_irregular_windows", "roof_geometry", "new_or_renovated"]
        
        widgets = {
            "self_similar_cluster": SelfSimilarClusterWidget(attrs={"class": "survey-1col"}),
            "has_simple_footprint": RadioSelect(choices=YES_NO, attrs={"class": "survey-1col"}),
            "has_simple_volume": RadioSelect(choices=YES_NO, attrs={"class": "survey-1col"}),
            "num_storeys": NumberOrUnsure(attrs={"class": "survey-1col"}),
            "has_basement": RadioSelect(choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}),
            "site_obstructions": MultiCheckboxSpecify(choices=SITE_OBSTRUCTIONS, has_specify=True, attrs={"class": "survey-1col"}),
            "appendages": MultiCheckboxSpecify(choices=APPENDAGES, has_specify=True, attrs={"class": "survey-1col"}),
            "exterior_cladding": MultiCheckboxSpecifyRequired(choices=FACADE_MATERIALS, has_specify=True, attrs={"class": "survey-3col"}),
            "facade_condition": RadioSelect(choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}),
            "window_wall_ratio": RadioSelect(choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}),
            "large_irregular_windows": MultiCheckboxSpecify(choices=WINDOWS, attrs={"class": "survey-1col"}),
            "roof_geometry": MultiCheckboxSpecifyRequired(choices=ROOF_GEOMETRIES, attrs={"class": "survey-3col"}),
            "new_or_renovated": MultiCheckboxSpecify(choices=NEW_OR_RENOVATED, attrs={"class": "survey-1col"}),
        }
        help_texts = {
            "self_similar_cluster": _("Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"),
            "has_simple_footprint": _("Does the building have a simple footprint?"),
            "has_simple_volume": _("Does the building have a simple volumetric form?"),
            "num_storeys": _("How many storeys above-ground does the building have?"),
            "has_basement": _("Does the building appear to have a basement?"),
            "site_obstructions": _("Select any and all obstructions to machine access around the building."),
            "appendages": _("Select any and all significant appendages to the building faces."),
            "exterior_cladding": _("Select all types of exterior cladding does the building appear to have."),
            "facade_condition": _("Are the façades in poor condition and in need of replacement?"),
            "window_wall_ratio": _("Does glazing make up more than 40% of the total visible façade area?"),
            "large_irregular_windows": _("Are there very large and/or irregularly shaped windows?"),
            "roof_geometry": _("Select all that describes the roof geometry?"),
            "new_or_renovated": _("Does the building look newly built or recently renovated?"),
        }

