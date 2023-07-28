from django.forms import widgets


class MyRadioSelect(widgets.RadioSelect):
    '''
    Radio select with CSS styling included
    '''
    template_name = "buildings/forms/widgets/my_radio.html"


class NumberOrUnsure(widgets.RadioSelect):
    '''
    Radio select with a number input
    '''
    template_name = "buildings/forms/widgets/number_or_unsure.html"

class CheckboxRequiredSelectMultiple(widgets.CheckboxSelectMultiple):
    '''
    Radio select with a number input
    '''
    template_name = "buildings/forms/widgets/checkbox_select.html"

    class Media:
        js = [
            "scripts/multi_checkbox_require.js",
        ]

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)

