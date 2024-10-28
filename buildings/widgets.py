from django.forms import widgets
import logging
from pprint import pprint

TW_RADIO_CLASS = """me-2 border-0 text-teal-600 accent-teal-600 focus:accent-teal-700 shadow-sm ring-1 focus:ring-2 focus:ring-teal-600"""

TW_SPECIFY_CLASS = """ms-1 specify rounded-md border-0 py-1 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""


class RadioSelect(widgets.RadioSelect):
    """
    Radio select with CSS styling included
    """

    template_name = "buildings/forms/widgets/radio.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None  # filled in by the form __init__()
        self.was_filled = None  # filled in by the form __init__()
        self.attrs["radio_class"] = TW_RADIO_CLASS

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        context["widget"]["was_filled"] = self.was_filled
        return context


class RadioWithSpecify(RadioSelect):
    """
    Radio select with CSS styling included
    """

    template_name = "buildings/forms/widgets/radio_w_specify.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None  # filled in by the form __init__()
        self.attrs["option_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        # The choices are a list of tuples, extract just the first member
        choice_keys = [c[0] for c in self.choices]
        # If initial exists, is not empty and is not in the choices then it was manually specified
        context["widget"]["value_was_specified"] = (
            self.initial and len(self.initial) > 0 and (self.initial not in choice_keys)
        )
        return context


class NumberOrUnsure(widgets.RadioSelect):
    """
    Radio select with a number input
    """

    template_name = "buildings/forms/widgets/number_or_unsure.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None  # filled in by the form __init__()
        self.was_filled = None  # filled in by the form __init__()
        self.attrs["radio_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        context["widget"]["was_filled"] = self.was_filled
        return context


class SelfSimilarClusterWidget(widgets.RadioSelect):
    """
    TODO: Refactor this and the NumberOrUnsure field together
    """

    template_name = "buildings/forms/widgets/self_similar_cluster.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None  # filled in by the form __init__()
        self.was_filled = None  # filled in by the form __init__()
        self.attrs["radio_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        context["widget"]["was_filled"] = self.was_filled
        return context


class MultiCheckboxSpecify(widgets.CheckboxSelectMultiple):

    template_name = "buildings/forms/widgets/multi_checkbox.html"

    class Media:
        js = [
            "scripts/multi_checkbox.js",
        ]

    def __init__(self, has_specify=False, input_type="checkbox", attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = []  # will be filled in in the form __init__()
        self.has_specify = has_specify
        self.input_type = input_type
        self.attrs["checkbox_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["has_specify"] = self.has_specify
        context["widget"]["input_type"] = self.input_type
        context["widget"]["initial"] = self.initial
        return context


class MultiCheckboxSpecifyRequired(MultiCheckboxSpecify):
    """
    Version with fields set as required
    """

    template_name = "buildings/forms/widgets/multi_checkbox_required.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.attrs["checkbox_class"] = TW_RADIO_CLASS
        self.attrs["specify_class"] = TW_SPECIFY_CLASS
