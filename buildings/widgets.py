from django.forms import widgets
import logging
from pprint import pprint

class RadioSelect(widgets.RadioSelect):
    '''
    Radio select with CSS styling included
    '''
    template_name = "buildings/forms/widgets/radio.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None # filled in by the form __init__()
        self.was_filled = None # filled in by the form __init__()

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        context["widget"]["was_filled"] = self.was_filled
        return context
        

class RadioWithSpecify(RadioSelect):
    '''
    Radio select with CSS styling included
    '''
    template_name = "buildings/forms/widgets/radio_w_specify.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None # filled in by the form __init__()

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        # The choices are a list of tuples, extract just the first member
        choice_keys = [c[0] for c in self.choices]
        # If initial exists, is not empty and is not in the choices then it was manually specified
        context["widget"]["value_was_specified"] = self.initial and len(self.initial) > 0 and (self.initial not in choice_keys)
        return context


class NumberOrUnsure(widgets.RadioSelect):
    '''
    Radio select with a number input
    '''
    template_name = "buildings/forms/widgets/number_or_unsure.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = None # filled in by the form __init__()
        self.was_filled = None # filled in by the form __init__()
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["initial"] = self.initial
        context["widget"]["was_filled"] = self.was_filled
        return context


class CheckboxSelectMultipleSpecifyRequired(widgets.CheckboxSelectMultiple):
    '''
    Radio select with a number input
    '''
    template_name = "buildings/forms/widgets/multi_checkbox_required.html"
    
    class Media:
        js = [
            "scripts/multi_checkbox_required.js",
        ]

    def __init__(self, has_specify=False, input_type="checkbox", attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = [] # will be filled in in the form __init__()
        self.has_specify = has_specify
        self.input_type = input_type

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["has_specify"] = self.has_specify
        context["widget"]["input_type"] = self.input_type
        context["widget"]["initial"] = self.initial
        return context

class CheckboxSelectMultipleSpecify(widgets.CheckboxSelectMultiple):
    '''
    Checkbox select multiple with an optional "specify" text input.
    '''
    template_name = "buildings/forms/widgets/multi_checkbox.html"
    
    class Media:
        js = [
            "scripts/multi_checkbox.js",
        ]

    def __init__(self, has_specify=False, input_type="checkbox", attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.initial = [] # will be filled in in the form __init__()
        self.has_specify = has_specify
        self.input_type = input_type

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["has_specify"] = self.has_specify
        context["widget"]["input_type"] = self.input_type
        context["widget"]["initial"] = self.initial
        return context
    


