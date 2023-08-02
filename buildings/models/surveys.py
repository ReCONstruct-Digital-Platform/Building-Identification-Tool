from pprint import pprint

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from buildings.models.models import Building

from buildings.widgets import RadioSelect, NumberOrUnsure, CheckboxRequiredSelectMultiple, RadioWithSpecify


YES_NO = [
    ("True", "Yes"),
    ("False", "No"),
]
YES_NO_UNSURE = [
    ("True", "Yes"),
    ("False", "No"),
    ("", "Unsure"),
]
SITE_OBSTRUCTIONS = [
    ("trees_or_landscaping", "Important trees or landscaping"),
    ("buildings", "Buildings"),
    ("overhead_wires", "Overhead wires, including those blocking general access to site"),
    ("no_obstructions", "No significant obstructions"),
]
APPENDAGES = [
    ("canopies_eaves", "Canopies/overhangs/eaves"),
    ("balconies", "Balconies"),
    ("porches_stoops", "Porches/stoops"),
    ("vestibules", "Vestibules"),
    ("none", "No significant appendages"),
]
FACADE_MATERIALS = [
    ("concrete", "Concrete"),
    ("plaster", "Plaster"),
    ("wood", "Wood"),
    ("vinyl", "Vinyl"),
    ("curtain_wall", "Curtain Wall"),
    ("metal", "Metal"),
    ("brick_masonry", "Brick Masonry"),
    ("stone_masonry", "Stone Masonry"),
    ("unsure", "Unsure"),
]
FACADE_CONDITIONS = [
    ("good", "Good"),
    ("fair", "Fair"),
    ("poor", "Poor"),
    ("unsure", "Unsure"),
]
WINDOW_TO_WALL_RATIOS = [
    ("small", "Small"),
    ("medium", "Medium"),
    ("large", "Large"),
    ("unsure", "Unsure"),
]
ROOF_GEOMETRIES = [
    ("flat", "Flat"),
    ("pitched", "Pitched"),
    ("curved", "Curved"),
    ("complex", "Complex"),
    ("unsure", "Unsure"),
]
STRUCTURE_TYPES = [
    ("wood_frame_light_gauge_steel", "Wood frame or light gauge steel"),
    ("concrete_frame", "Concrete frame"),
    ("steel_frame", "Steel frame"),
    ("brick_masonry", "Load-bearing brick masonry"),
    ("stone_masonry", "Load-bearing stone masonry"),
    ("unsure", "Unsure"),
]

class BaseSurvey(models.Model):
    """
    A survey is created by a user, about a building.
    Each user can only vote on a survey once for a given building.
    """
    class Meta:
        unique_together = (('user','building'),)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    creation_date = models.DateTimeField('date created', default=timezone.now)
    last_modified = models.DateTimeField('last modified', default=timezone.now)


class SurveyV1(BaseSurvey):
    has_simple_footprint = models.BooleanField()
    has_simple_volume = models.BooleanField()
    num_storeys = models.IntegerField(blank=True, null=True)
    has_basement = models.BooleanField(blank=True, null=True)
    site_obstructions = models.JSONField() # checkbox multiple w specify
    appendages = models.JSONField() # checkbox multiple w specify
    exterior_cladding = models.JSONField() # checkbox multiple w specify
    facade_condition = models.TextField(blank=True, null=True) # radio
    window_wall_ratio = models.TextField(blank=True, null=True) # radio
    large_irregular_windows = models.BooleanField(blank=True, null=True) # radio
    roof_geometry = models.TextField() # radio w specify 
    structure_type = models.TextField() # radio w specify 
    new_or_renovated = models.BooleanField(blank=True, null=True) # radio


 
class SurveyV1Form(ModelForm):
    # Some reading:
    # https://docs.djangoproject.com/en/4.2/ref/forms/api/
    # https://docs.djangoproject.com/en/4.2/topics/forms/modelforms/
    # https://docs.djangoproject.com/en/4.2/ref/forms/widgets/
    # https://docs.djangoproject.com/en/4.2/ref/forms/validation/

    template_name = "surveys/survey_v1.html"
    json_fields = ['site_obstructions', 'appendages', 'exterior_cladding']

    def __init__(self, *data, **kwargs):
        super().__init__(*data, **kwargs)

        # Add initial values to the widgets
        for field in self.fields:
            if field in self.initial:
                self.fields[field].widget.initial = self.initial[field]
        

    class Meta:
        model = SurveyV1

        fields = ["has_simple_footprint", "has_simple_volume", "num_storeys", "has_basement", 
                  "site_obstructions", "appendages", "exterior_cladding", "facade_condition", 
                  "window_wall_ratio", "large_irregular_windows", "roof_geometry", "structure_type", 
                  "new_or_renovated"]
        
        widgets = {
            "has_simple_footprint": RadioSelect(choices=YES_NO, attrs={"class": "survey-1col"}),
            "has_simple_volume": RadioSelect(choices=YES_NO, attrs={"class": "survey-1col"}),
            "num_storeys": NumberOrUnsure(attrs={"class": "survey-1col"}),
            "has_basement": RadioSelect(choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}),
            "site_obstructions": CheckboxRequiredSelectMultiple(choices=SITE_OBSTRUCTIONS, has_specify=True, attrs={"class": "survey-1col"}),
            "appendages": CheckboxRequiredSelectMultiple(choices=APPENDAGES, has_specify=True, attrs={"class": "survey-1col"}),
            "exterior_cladding": CheckboxRequiredSelectMultiple(choices=FACADE_MATERIALS, has_specify=True, attrs={"class": "survey-3col"}),
            "facade_condition": RadioSelect(choices=FACADE_CONDITIONS, attrs={"class": "survey-2col"}),
            "window_wall_ratio": RadioSelect(choices=WINDOW_TO_WALL_RATIOS, attrs={"class": "survey-1col"}),
            "large_irregular_windows": RadioSelect(choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}),
            "roof_geometry": RadioWithSpecify(choices=ROOF_GEOMETRIES, has_specify=True, attrs={"class": "survey-3col"}),
            "structure_type": RadioWithSpecify(choices=STRUCTURE_TYPES, has_specify=True, attrs={"class": "survey-2col"}),
            "new_or_renovated": RadioSelect(choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}),
        }
        help_texts = {
            "has_simple_footprint": _("Does the building have a simple footprint?"),
            "has_simple_volume": _("Does the building have a simple volumetric form?"),
            "num_storeys": _("How many storeys above-ground does the building have?"),
            "has_basement": _("Does the building have a basement?"),
            "site_obstructions": _("Are there obstructions to machine access around the building (within 3m or less)? Select all that apply."),
            "appendages": _("Are there significant appendages to the building faces? Select all that apply."),
            "exterior_cladding": _("What type of exterior cladding does the building appear to have? Select all that apply."),
            "facade_condition": _("How would you describe the condition of the exterior façades?"),
            "window_wall_ratio": _("Is there a large proportion of windows to overall façade area?"),
            "large_irregular_windows": _("Are there very large and/or irregularly shaped windows?"),
            "roof_geometry": _("What best describes the roof geometry?"),
            "structure_type": _("What type of structure does the building appear to have?"),
            "new_or_renovated": _("Does this building look new and/or recently renovated?"),
        }

