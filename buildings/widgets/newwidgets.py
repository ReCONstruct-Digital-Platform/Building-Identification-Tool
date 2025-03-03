from django.forms import widgets
import logging
from pprint import pprint

TW_RADIO_CLASS = """me-2 text-base border-0 text-teal-600 accent-teal-600 focus:accent-teal-700 shadow-sm ring-1 focus:ring-2 focus:ring-teal-600"""

TW_SPECIFY_CLASS = """ms-1 h-[30px] text-base rounded-md border-0 py-1 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600"""


class RadioSelect(widgets.RadioSelect):
    """
    Radio select with CSS styling included
    """

    template_name = "buildings/forms/widgets/radio.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.is_bound = False
        self.attrs["radio_class"] = TW_RADIO_CLASS

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["is_bound"] = self.is_bound
        return context


class RadioSelectForFieldForm(widgets.RadioSelect):
    template_name = "buildings/forms/widgets/radio_4_field_form.html"


class DropdownSelectForFieldForm(widgets.Select):
    template_name = "buildings/forms/widgets/select_4_field_form.html"


class RadioWithSpecify2(widgets.RadioSelect):
    """
    Radio select with CSS styling included
    """

    template_name = "buildings/forms/widgets/radio_w_specify_2.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None
        self.is_bound = False
        self.specify_input_type = None
        self.specify_option_value = None
        self.has_modal = None
        self.modal = None
        self.attrs["option_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    # Add attributes you want available in the template to the context
    # Note that while value in the optgroups method is and array of strings
    # here it is the actual value contained within
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["specify_input_type"] = self.specify_input_type
        context["widget"]["specify_option_value"] = self.specify_option_value
        context["widget"]["modal"] = self.modal
        context["widget"]["has_modal"] = self.has_modal
        context["widget"]["is_bound"] = self.is_bound

        choice_keys = [c[0] for c in self.choices]
        context["widget"]["value_was_specified"] = value and (value not in choice_keys)
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
        self.is_bound = False
        self.is_required = False
        self.specify_input_type = "text"
        self.specify_option_value = "other"
        self.attrs["checkbox_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    # Add attributes you want available in the template to the context
    # Gets called with the value of the bound field
    def get_context(self, name, value, attrs):
        # Value is an array of all selected - no subarray at this stage
        # or None if unbound
        # When non-required field was left empty, value will be empty array as well
        # and field will be marked as bound as there is a key for field in data
        if not value:
            value = []
        context = super().get_context(name, value, attrs)
        context["widget"]["input_type"] = self.input_type
        context["widget"]["has_specify"] = self.has_specify
        context["widget"]["is_required"] = self.is_required
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
