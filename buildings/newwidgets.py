from django.forms import widgets
import logging
from pprint import pprint

TW_RADIO_CLASS = """me-2 text-xs border-0 text-teal-600 accent-teal-600 focus:accent-teal-700 shadow-sm ring-1 focus:ring-2 focus:ring-teal-600"""

TW_SPECIFY_CLASS = """ms-1 text-xs specify rounded-md border-0 py-1 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""


class RadioSelect(widgets.RadioSelect):
    """
    Radio select with CSS styling included
    """

    template_name = "buildings/forms/widgets/radio.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None  # filled in by the form __init__()
        self.attrs["radio_class"] = TW_RADIO_CLASS

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        return context


class RadioWithSpecify2(widgets.RadioSelect):
    """
    Radio select with CSS styling included
    """

    template_name = "buildings/forms/widgets/radio_w_specify_2.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def format_value(self, value):
        """Return selected values as a list."""
        # Try returning None here
        if value is None and self.allow_multiple_selected:
            return None
        if not isinstance(value, (tuple, list)):
            value = [value]
        return [str(v) for v in value]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None
        self.specify_input_type = None
        self.specify_option_value = None
        self.has_modal = None
        self.modal = None
        self.attrs["option_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # The choices are a list of tuples, extract just the first member
        choice_keys = [c[0] for c in self.choices]
        # If initial exists, is not empty and is not in the choices then it was manually specified
        context["widget"]["initial"] = self.initial
        context["widget"]["value_was_specified"] = value and (value not in choice_keys)
        context["widget"]["specify_input_type"] = self.specify_input_type
        context["widget"]["specify_option_value"] = self.specify_option_value
        context["widget"]["modal"] = self.modal
        context["widget"]["has_modal"] = self.has_modal
        return context


class MultiCheckboxSpecify2(widgets.CheckboxSelectMultiple):

    template_name = "buildings/forms/widgets/multi_checkbox_2.html"

    class Media:
        js = [
            "scripts/multi_checkbox.js",
        ]

    def __init__(self, has_specify=False, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.has_specify = has_specify
        self.specify_input_type = "text"
        self.specify_option_value = "other"
        self.attrs["checkbox_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    # Add attributes you want available in the template to the context
    # Gets called with the value of the bound field
    def get_context(self, name, value, attrs):
        if not value:
            value = []
        context = super().get_context(name, value, attrs)
        context["widget"]["input_type"] = self.input_type
        context["widget"]["has_specify"] = self.has_specify
        context["widget"]["specify_input_type"] = self.specify_input_type
        context["widget"]["specify_option_value"] = self.specify_option_value
        # The choices are a list of tuples, extract just the first member
        choice_keys = {c[0] for c in self.choices}

        # Iterate through the initial widget values
        # The one that's not in the choices was specified
        if value:
            for i in value:
                if i not in choice_keys:
                    context["widget"]["value_was_specified"] = True
                    context["widget"]["specified_value"] = i
                    break
        else:
            context["widget"]["value_was_specified"] = False
            context["widget"]["specified_value"] = None
        return context


class MultiCheckboxSpecifyRequired2(MultiCheckboxSpecify2):
    """
    Version with fields set as required
    """

    template_name = "buildings/forms/widgets/multi_checkbox_required_2.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.attrs["checkbox_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS
