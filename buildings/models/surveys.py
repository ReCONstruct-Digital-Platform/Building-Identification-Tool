import logging
from pprint import pprint
from copy import deepcopy

from django import forms
from django.db import models
from django.forms import ModelForm, Form
from django.utils.translation import gettext_lazy as _

from buildings.models.models import Vote

from buildings.widgets import (
    MultiCheckboxSpecify,
    MultiCheckboxSpecify2,
    MultiCheckboxSpecifyRequired2,
    RadioSelect,
    NumberOrUnsure,
    MultiCheckboxSpecifyRequired,
    RadioWithSpecify2,
    SelfSimilarClusterWidget,
)


# The first element is the actual value
# forms will pass it as a string nack to the backend
YES_NO = [
    (True, _("Yes")),
    (False, _("No")),
]
YES_NO_UNSURE = [
    (True, _("Yes")),
    (False, _("No")),
    (None, _("Unsure")),
]
SITE_OBSTRUCTIONS = [
    ("trees_or_landscaping", _("Important trees or landscaping")),
    ("buildings", _("Buildings")),
    (
        "overhead_wires",
        _("Overhead wires, incl. those blocking general access to site"),
    ),
]
APPENDAGES = [
    ("canopies_eaves", _("Roof overhangs/eaves")),
    ("balconies", _("Balconies")),
    ("porches_stoops", _("Porches/stoops")),
    ("vestibules", _("Exterior Vestibules")),
]
FACADE_MATERIALS = [
    ("brick_masonry", _("Brick Masonry")),
    ("concrete", _("Concrete")),
    ("curtain_wall", _("Curtain Wall")),
    ("plaster", _("Plaster")),
    ("metal", _("Metal")),
    ("vinyl", _("Vinyl")),
    ("stone_masonry", _("Stone Masonry")),
    ("wood", _("Wood")),
    ("unsure", _("Unsure")),
]
ROOF_GEOMETRIES = [
    ("flat", _("Flat")),
    ("pitch_low", _("Low Pitched")),
    ("pitch_high", _("High Pitched")),
    ("curved", _("Curved")),
    ("complex", _("Complex")),
    ("unsure", _("Unsure")),
]

# TODO: We might re-use this question for expert users at a later time
STRUCTURE_TYPES = [
    ("wood_frame_light_gauge_steel", _("Wood frame or light gauge steel")),
    ("concrete_frame", _("Concrete frame")),
    ("steel_frame", _("Steel frame")),
    ("brick_masonry", _("Load-bearing brick masonry")),
    ("stone_masonry", _("Load-bearing stone masonry")),
    ("unsure", "Unsure"),
]
WINDOWS = [
    ("very_large_windows", _("Very large")),
    ("irregular_windows", _("Irregularly shaped")),
]
NEW_OR_RENOVATED = [
    ("newly_built", _("Newly built")),
    ("recently_renovated", _("Recently renovated")),
]

WIDGETS = {
    "radio": RadioSelect(attrs={"class": "survey-1col"}),
    "radio_w_specify": RadioWithSpecify2(attrs={"class": "survey-1col"}),
    "multi_checkbox": MultiCheckboxSpecify2(
        attrs={"class": "survey-1col"}, has_specify=False
    ),
    "multi_checkbox_specify": MultiCheckboxSpecify2(
        attrs={"class": "survey-1col"}, has_specify=True
    ),
    "multi_checkbox_required": MultiCheckboxSpecifyRequired2(
        attrs={"class": "survey-3col"},
    ),
    "multi_checkbox_required_specify": MultiCheckboxSpecifyRequired2(
        attrs={"class": "survey-3col"},
        has_specify=True,
    ),
}

test_schema = {
  "appendages": {
    "label": { "en": "Appendages" },
    "options": {
      "balconies": { "option_text": { "en": "Balconies" } },
      "vestibules": { "option_text": { "en": "Exterior Vestibules" } },
      "canopies_eaves": { "option_text": { "en": "Roof overhangs/eaves" } },
      "porches_stoops": { "option_text": { "en": "Porches/stoops" } },
      "other": { "option_text": { "en": "Other (specify)" } }
    },
    "widget": "multi_checkbox_specify",
    "widget_config": {
      "specify_input_type": "text",
      "specify_option_value": "other",
      "attrs": { "class": "survey-1col" }
    },
    "question_text": {
      "en": "Select any and all significant appendages to the building faces."
    },
    "question_number": 7
  },
  "num_storeys": {
    "label": { "en": "Number of Storeys" },
    "widget": "radio_w_specify",
    "widget_config": {
      "specify_input_type": "number",
      "specify_option_value": "num_storeys",
      "attrs": { "class": "survey-1col" }
    },
    "options": {
      "num_storeys": {
        "option_text": { "en": "Number of storeys:" }
      },
      "unsure": { "option_text": { "en": "Unsure" } }
    },
    "question_text": {
      "en": "How many storeys above-ground does the building have?"
    },
    "question_number": 4
  },
  "has_basement": {
    "label": { "en": "Has Basement" },
    "widget": "radio",
    "type": "boolean_3_choices",
    "widget_config": {
      "attrs": { "class": "survey-1col" }
    },
    "options": {
      "true": { "option_text": { "en": "Yes" } },
      "false": { "option_text": { "en": "No" } },
      "other": { "option_text": { "en": "Unsure" } }
    },
    "question_text": { "en": "Does the building appear to have a basement?" },
    "question_number": 5
  },
  "roof_geometry": {
    "label": { "en": "Roof Geometry" },
    "options": {
      "flat": { "option_text": { "en": "Flat" } },
      "curved": { "option_text": { "en": "Curved" } },
      "unsure": { "option_text": { "en": "Unsure" } },
      "complex": { "option_text": { "en": "Complex" } },
      "pitch_low": { "option_text": { "en": "Low Pitched" } },
      "pitch_high": { "option_text": { "en": "High Pitched" } }
    },
    "widget": "multi_checkbox_required",
    "widget_config": {
      "attrs": { "class": "survey-3col" }
    },
    "question_text": { "en": "Select all that describes the roof geometry." },
    "question_number": 12
  },
  "facade_condition": {
    "label": { "en": "Facade Condition" },
    "widget": "radio",
    "type": "boolean_3_choices",
    "widget_config": {
      "attrs": { "class": "survey-1col" }
    },
    "options": {
      "true": { "option_text": { "en": "Yes" } },
      "false": { "option_text": { "en": "No" } },
      "other": { "option_text": { "en": "Unsure" } }
    },
    "question_text": {
      "en": "Are the façades in poor condition and in need of replacement?"
    },
    "question_number": 9
  },
  "new_or_renovated": {
    "label": { "en": "New or Renovated" },
    "options": {
      "newly_built": { "option_text": { "en": "Newly built" } },
      "recently_renovated": { "option_text": { "en": "Recently renovated" } }
    },
    "widget": "multi_checkbox",
    "question_text": {
      "en": "Does the building look newly built or recently renovated?"
    },
    "question_number": 13
  },
  "exterior_cladding": {
    "label": { "en": "Exterior Cladding" },
    "options": {
      "wood": { "option_text": { "en": "Wood" } },
      "metal": { "option_text": { "en": "Metal" } },
      "vinyl": { "option_text": { "en": "Vinyl" } },
      "unsure": { "option_text": { "en": "Unsure" } },
      "plaster": { "option_text": { "en": "Plaster" } },
      "concrete": { "option_text": { "en": "Concrete" } },
      "curtain_wall": { "option_text": { "en": "Curtain Wall" } },
      "brick_masonry": { "option_text": { "en": "Brick Masonry" } },
      "stone_masonry": { "option_text": { "en": "Stone Masonry" } },
      "other": { "option_text": { "en": "Other (Specify)" } }
    },
    "widget": "multi_checkbox_required_specify",
    "widget_config": {
      "attrs": { "class": "survey-3col" },
      "specify_input_type": "text",
      "specify_option_value": "other"
    },
    "question_text": {
      "en": "Select all widgets of exterior cladding does the building appear to have."
    },
    "question_number": 8
  },
  "has_simple_volume": {
    "label": { "en": "Simple Volume" },
    "widget": "radio",
    "type": "boolean_2_choices",
    "options": {
      "true": { "option_text": { "en": "Yes" } },
      "false": { "option_text": { "en": "No" } }
    },
    "question_text": {
      "en": "Does the building have a simple volumetric form?"
    },
    "question_number": 3
  },
  "site_obstructions": {
    "label": { "en": "Site Obstructions" },
    "options": {
      "buildings": { "option_text": { "en": "Buildings" } },
      "overhead_wires": {
        "option_text": {
          "en": "Overhead wires, incl. those blocking general access to site"
        }
      },
      "trees_or_landscaping": {
        "option_text": { "en": "Important trees or landscaping" }
      }
    },
    "widget": "multi_checkbox_specify",
    "question_text": {
      "en": "Select any and all obstructions to machine access around the building."
    },
    "question_number": 6
  },
  "window_wall_ratio": {
    "label": { "en": "Window-to-Wall Ratio"},
    "widget": "radio",
    "type": "boolean_3_choices",
    "widget_config": {
      "attrs": { "class": "survey-1col" }
    },
    "options": {
      "true": { "option_text": { "en": "Yes" } },
      "false": { "option_text": { "en": "No" } },
      "other": { "option_text": { "en": "Unsure" } }
    },
    "question_text": {
      "en": "Does glazing make up more than 40% of the total visible façade area?"
    },
    "question_number": 10
  },
  "has_simple_footprint": {
    "label": { "en": "Simple Footprint" },
    "widget": "radio",
    "type": "boolean_2_choices",
    "options": {
      "true": { "option_text": { "en": "Yes" } },
      "false": { "option_text": { "en": "No" } }
    },
    "question_text": { "en": "Does the building have a simple footprint?" },
    "question_number": 2
  },
  "self_similar_cluster": {
    "label": {"en": "Self Similar Cluster"},
    "widget": "radio_w_specify",
    "widget_config": {
        "specify_input_type": "number",
        "specify_option_value": "num_buildings_in_cluster"
    },
    "options": {
        "num_buildings_in_cluster": {
            "option_text": {"en": "Buildings in cluster:"}
        },
        "no_cluster": {"option_text": {"en": "No"}}
    },
    "question_text": {
        "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
    },
    "question_number": 1
  },
  "large_irregular_windows": {
    "label": { "en": "Large/Irregular Windows"},
    "widget": "multi_checkbox",
    "widget_config": {
      "attrs": { "class": "survey-1col" }
    },
    "options": {
      "very_large_windows": { "option_text": { "en": "Very large" } },
      "irregular_windows": { "option_text": { "en": "Irregularly shaped" } }
    },
    "question_text": {
      "en": "Are there very large and/or irregularly shaped windows?"
    },
    "question_number": 11
  }
}


def order_schema_by_question_number(schema):
    return dict(sorted(schema.items(), key=lambda x: x[1]["question_number"]))


class DynamicSurveyForm(Form):
    def __init__(self, schema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        schema = order_schema_by_question_number(test_schema)

        for field, config in schema.items():
            self.fields[field] = forms.IntegerField()
            self.fields[field].label = config["label"]["en"]
            self.fields[field].widget = deepcopy(WIDGETS[config["widget"]])
            self.fields[field].question_text = config["question_text"]["en"]
            self.fields[field].question_number = config["question_number"]

            if "widget_config" in config:
                for k, v in config["widget_config"].items():
                    # We don't want to overwrite any existing attrs
                    if k == "attrs":
                        for k, v in config["widget_config"]["attrs"].items():
                            self.fields[field].widget.attrs[k] = v
                    else:
                        setattr(self.fields[field].widget, k, v)

            if "options" in config:
                self.fields[field].widget.choices = [
                    (k, _(v["option_text"]["en"])) for k, v in config["options"].items()
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
    site_obstructions = JSONFieldForSpecify(
        blank=True, null=True
    )  # checkbox multiple w specify not required
    appendages = JSONFieldForSpecify(
        blank=True, null=True
    )  # checkbox multiple w specify not required
    exterior_cladding = JSONFieldForSpecify()  # checkbox multiple w specify
    facade_condition = models.BooleanField(blank=True, null=True)  # radio
    window_wall_ratio = models.BooleanField(blank=True, null=True)  # radio
    large_irregular_windows = models.JSONField(
        blank=True, null=True
    )  # checkbox multiple not required
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
    json_fields = ["site_obstructions", "appendages", "exterior_cladding"]
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
        if "instance" in kwargs and kwargs["instance"]:
            self.was_filled = True

            # Add initial values to the widgets
            for field in self.fields:
                self.fields[field].widget.was_filled = self.was_filled
                self.fields[field].widget.initial = self.initial[field]

    class Meta:
        model = SurveyV1

        fields = [
            "self_similar_cluster",
            "has_simple_footprint",
            "has_simple_volume",
            "num_storeys",
            "has_basement",
            "site_obstructions",
            "appendages",
            "exterior_cladding",
            "facade_condition",
            "window_wall_ratio",
            "large_irregular_windows",
            "roof_geometry",
            "new_or_renovated",
        ]

        widgets = {
            "self_similar_cluster": SelfSimilarClusterWidget(
                attrs={"class": "survey-1col"}
            ),
            "has_simple_footprint": RadioSelect(
                choices=YES_NO, attrs={"class": "survey-1col"}
            ),
            "has_simple_volume": RadioSelect(
                choices=YES_NO, attrs={"class": "survey-1col"}
            ),
            "num_storeys": NumberOrUnsure(attrs={"class": "survey-1col"}),
            "has_basement": RadioSelect(
                choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}
            ),
            "site_obstructions": MultiCheckboxSpecify(
                choices=SITE_OBSTRUCTIONS,
                has_specify=True,
                attrs={"class": "survey-1col"},
            ),
            "appendages": MultiCheckboxSpecify(
                choices=APPENDAGES, has_specify=True, attrs={"class": "survey-1col"}
            ),
            "exterior_cladding": MultiCheckboxSpecifyRequired(
                choices=FACADE_MATERIALS,
                has_specify=True,
                attrs={"class": "survey-3col"},
            ),
            "facade_condition": RadioSelect(
                choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}
            ),
            "window_wall_ratio": RadioSelect(
                choices=YES_NO_UNSURE, attrs={"class": "survey-1col"}
            ),
            "large_irregular_windows": MultiCheckboxSpecify(
                choices=WINDOWS, attrs={"class": "survey-1col"}
            ),
            "roof_geometry": MultiCheckboxSpecifyRequired(
                choices=ROOF_GEOMETRIES, attrs={"class": "survey-3col"}
            ),
            "new_or_renovated": MultiCheckboxSpecify(
                choices=NEW_OR_RENOVATED, attrs={"class": "survey-1col"}
            ),
        }
        help_texts = {
            "self_similar_cluster": _(
                "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
            ),
            "has_simple_footprint": _("Does the building have a simple footprint?"),
            "has_simple_volume": _("Does the building have a simple volumetric form?"),
            "num_storeys": _("How many storeys above-ground does the building have?"),
            "has_basement": _("Does the building appear to have a basement?"),
            "site_obstructions": _(
                "Select any and all obstructions to machine access around the building."
            ),
            "appendages": _(
                "Select any and all significant appendages to the building faces."
            ),
            "exterior_cladding": _(
                "Select all types of exterior cladding does the building appear to have."
            ),
            "facade_condition": _(
                "Are the façades in poor condition and in need of replacement?"
            ),
            "window_wall_ratio": _(
                "Does glazing make up more than 40% of the total visible façade area?"
            ),
            "large_irregular_windows": _(
                "Are there very large and/or irregularly shaped windows?"
            ),
            "roof_geometry": _("Select all that describes the roof geometry?"),
            "new_or_renovated": _(
                "Does the building look newly built or recently renovated?"
            ),
        }
