import json
from django import forms
from django.forms import ValidationError, widgets
from django.http import QueryDict
from buildings.newwidgets import RadioSelectForFieldForm
from django.utils.translation import gettext_lazy as _


# Override these widgets to make them have unique IDs
# (This avoid focus going to another elemnt with the same id when clicking out of the input)
# We don't want to use prefix as we DO want the input names to be the same,
# which is done by default in Boundfield init(). So here we explicitly giving
# the ID we want to the widget. We could also generate a random value.
class TextInputWidget(widgets.TextInput):
    def get_context(self, name, value, attrs):
        attrs |= {"id": f"text_area_{self.field_num}"}
        context = super().get_context(name, value, attrs)
        return context


class TextAreaWidget(widgets.Textarea):
    def get_context(self, name, value, attrs):
        attrs |= {"id": f"text_input_{self.field_num}"}
        context = super().get_context(name, value, attrs)
        return context


class DragListWidget(widgets.CheckboxSelectMultiple):
    """
    List with draggable elements. Needs JS code to enable drag.
    """

    template_name = "buildings/forms/widgets/draglist.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context

    def format_value(self, value):
        """
        Don't convert to string
        """
        return value


class ListField(forms.Field):

    def to_python(self, value):
        super().to_python(value)
        if isinstance(value, str):
            return json.loads(value)
        return value

    def prepare_value(self, value):
        # Don't cast to string, we want it as a list for template rendering
        return value


class BaseNewFieldForm(forms.Form):
    TW_DEFAULT_CLASS = """w-1/2 rounded-md border-0 py-1.5shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600"""

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = self.TW_DEFAULT_CLASS
            field.widget.field_num = field_num

    field_label = forms.CharField(
        label=_("Field Label"),
        initial="Field Label",
        max_length=100,
        widget=TextInputWidget(attrs={"autocomplete": "off"}),
    )
    question_text = forms.CharField(
        label=_("Question Text"),
        max_length=500,
        widget=TextAreaWidget(attrs={"rows": 2}),
    )


class OptionsFieldForm(BaseNewFieldForm):

    TW_OPTIONS_CLASS = """rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600"""

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(field_num, *args, **kwargs)

    can_add_options = False

    options = ListField(
        label=_("Options"), widget=DragListWidget(attrs={"class": TW_OPTIONS_CLASS})
    )

    def clean_options(self):
        """
        Ensures all options provided are unique
        """
        value = self.cleaned_data["options"]
        opt_counts = {}
        for opt in value:
            if opt in opt_counts:
                opt_counts[opt] += 1
            else:
                opt_counts[opt] = 1

        opt_errors = []
        for opt, count in opt_counts.items():
            if count > 1:
                opt_errors.append(f"{opt} was repeated {count} times")
        if opt_errors:
            opt_errors = ", ".join(opt_errors)
            raise ValidationError("Options should be unique. " + opt_errors)

        return value


class OptionsFieldFormArbitraryOptions(OptionsFieldForm):

    num_columns = forms.ChoiceField(
        label=_("Num Columns"),
        widget=RadioSelectForFieldForm(
            attrs={"class": "grid grid-cols-3 gap-2"},
        ),
        choices=((1, _("1")), (2, _("2")), (3, _("3"))),
    )

    can_add_options = True


class OptionsFieldFormForRadioInputs(OptionsFieldFormArbitraryOptions):
    # Radios are always required
    pass


class OptionsFieldFormForCheckboxes(OptionsFieldFormArbitraryOptions):

    is_required = forms.ChoiceField(
        label=_("Is Required?"),
        widget=RadioSelectForFieldForm(
            attrs={"class": "grid grid-cols-3 gap-2"},
        ),
        choices=((False, _("No")), (True, _("Yes"))),
    )


class RadioFieldWithSpecify(OptionsFieldFormForRadioInputs):

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(field_num, *args, **kwargs)
        # Fucking QUERYDICT returning only the last element of LISTS silently
        # Python is NOT the language to pull this FUCKERY
        if isinstance(self.data, QueryDict):
            options = self.data.getlist("options")
        else:
            options = self.data["options"]

        # Has to have been set as bound data on Form creation to work!
        options_choices = [(opt, opt) for opt in options]
        self.fields["specify_option"].choices = list(options_choices)

    specify_option = forms.ChoiceField(
        label=_("Specify Option"), widget=widgets.Select()
    )

    has_specify = True


class CheckboxFieldWithSpecify(OptionsFieldFormForCheckboxes):

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(field_num, *args, **kwargs)
        # Fucking QUERYDICT returning only the last element of LISTS silently
        # Python is NOT the language to pull this FUCKERY
        if isinstance(self.data, QueryDict):
            options = self.data.getlist("options")
        else:
            options = self.data["options"]

        # Has to have been set as bound data on Form creation to work!
        options_choices = [(opt, opt) for opt in options]
        self.fields["specify_option"].choices = list(options_choices)

    specify_option = forms.ChoiceField(
        label=_("Specify Option"), widget=widgets.Select()
    )

    has_specify = True
