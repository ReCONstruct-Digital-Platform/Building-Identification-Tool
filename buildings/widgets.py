from django.forms import widgets


class RadioSelect(widgets.RadioSelect):
    '''
    Radio select with CSS styling included
    '''
    template_name = "buildings/forms/widgets/radio.html"

class RadioWithSpecify(RadioSelect):
    '''
    Radio select with CSS styling included
    '''
    template_name = "buildings/forms/widgets/radio_w_specify.html"

    class Media:
        js = [
            "scripts/specify.js",
        ]

    def __init__(self, has_specify=False, attrs=None, **kwargs):
        self.has_specify = has_specify
        super().__init__(attrs=attrs, **kwargs)

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["has_specify"] = self.has_specify
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

class CheckboxRequiredSelectMultiple(widgets.CheckboxSelectMultiple):
    '''
    Radio select with a number input
    '''
    template_name = "buildings/forms/widgets/multi_checkbox_required.html"
    
    class Media:
        js = [
            "scripts/multi_checkbox_required.js",
        ]

    def __init__(self, has_specify=False, input_type="checkbox", attrs=None, **kwargs):
        self.has_specify = has_specify
        self.input_type = input_type
        super().__init__(attrs=attrs, **kwargs)

    # Add attributes you want available in the template to the context
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["has_specify"] = self.has_specify
        context["widget"]["input_type"] = self.input_type
        return context

