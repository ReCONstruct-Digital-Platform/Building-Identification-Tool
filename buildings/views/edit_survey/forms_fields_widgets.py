import json
from django import forms
from django.forms import ValidationError, widgets
from django.http import QueryDict
from buildings.widgets import RadioSelectForFieldForm
from django.utils.translation import gettext_lazy as _

from buildings.widgets.newwidgets import DropdownSelectForFieldForm


# Override these widgets to make them have unique IDs
# (This avoid focus going to another elemnt with the same id when clicking out of the input)
# We don't want to use prefix as we DO want the input names to be the same,
# which is done by default in Boundfield init(). So here we explicitly giving
# the ID we want to the widget. We could also generate a random value.
class TextInputWidget(widgets.TextInput):
    def get_context(self, name, value, attrs):
        attrs |= {"id": f"text_area_{self.field_num}"}
        if self.disabled:
            attrs |= {"disabled": True}
        context = super().get_context(name, value, attrs)
        return context


class TextAreaWidget(widgets.Textarea):
    def get_context(self, name, value, attrs):
        attrs |= {"id": f"text_input_{self.field_num}"}
        if self.disabled:
            attrs |= {"disabled": True}
        context = super().get_context(name, value, attrs)
        return context


class IntegerInputWidget(widgets.NumberInput):
    def get_context(self, name, value, attrs):
        attrs |= {"id": f"number_{self.field_num}"}
        if self.disabled:
            attrs |= {"disabled": True}
        context = super().get_context(name, value, attrs)
        return context


class DragListWidget(widgets.CheckboxSelectMultiple):
    """
    List with draggable elements. Needs JS code to enable drag.
    """

    template_name = "buildings/forms/widgets/draglist.html"

    def __init__(self, attrs=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        self.can_add_options = False

    def get_context(self, name, value, attrs):
        if self.disabled:
            attrs |= {"disabled": True}
        context = super().get_context(name, value, attrs)
        context["widget"]["can_add_options"] = self.can_add_options
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
    TW_DEFAULT_CLASS = """rounded-md border-0 py-1.5shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-500 disabled:shadow-none"""

    def __init__(self, field_num, *args, **kwargs):
        self.is_disabled = kwargs.pop("disabled", True)
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = self.TW_DEFAULT_CLASS
            field.widget.field_num = field_num
            field.widget.disabled = self.is_disabled

    has_options = False

    field_label = forms.CharField(
        label=_("Field Label"),
        initial="Field Label",
        max_length=100,
        widget=TextInputWidget(attrs={"autocomplete": "off"}),
    )
    question_text = forms.CharField(
        label=_("Question Text"),
        max_length=500,
        widget=TextAreaWidget(attrs={"rows": 1}),
    )


class NumberFieldForm(BaseNewFieldForm):

    def clean(self):
        min_value = self.cleaned_data.get("min_value")
        max_value = self.cleaned_data.get("max_value")

        if min_value is not None and max_value is not None:
            if min_value > max_value:
                raise ValidationError("Min value cannot be greater than max value")

    min_value = forms.IntegerField(
        label=_("Min Value"), required=False, widget=IntegerInputWidget()
    )
    max_value = forms.IntegerField(
        label=_("Max Value"), required=False, widget=IntegerInputWidget()
    )

    is_required = forms.ChoiceField(
        label=_("Is Required?"),
        widget=RadioSelectForFieldForm(
            attrs={"class": "flex flex-row gap-8"},
        ),
        choices=((False, _("No")), (True, _("Yes"))),
    )

    number_type = forms.ChoiceField(
        label=_("Type"),
        widget=RadioSelectForFieldForm(
            attrs={"class": "flex flex-row gap-8"},
        ),
        choices=(("integer", _("Whole number")), ("float", _("Decimal"))),
    )


class TextFieldForm(BaseNewFieldForm):

    is_required = forms.ChoiceField(
        label=_("Is Required?"),
        widget=RadioSelectForFieldForm(
            attrs={"class": "flex flex-row gap-8"},
        ),
        choices=((False, _("No")), (True, _("Yes"))),
    )
    num_lines = forms.IntegerField(label=_("Num Lines"), min_value=0)


class OptionsFieldForm(BaseNewFieldForm):

    TW_OPTIONS_CLASS = """rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-500 disabled:shadow-none"""

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(field_num, *args, **kwargs)

        for field in self.fields.values():
            field.widget.can_add_options = self.can_add_options

    has_options = True
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
            attrs={"class": "flex flex-row gap-8"},
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
            attrs={"class": "flex flex-row gap-8"},
        ),
        choices=((False, _("No")), (True, _("Yes"))),
    )


class RadioFieldWithSpecifyForm(OptionsFieldFormForRadioInputs):

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
        label=_("Specify Option"), widget=DropdownSelectForFieldForm()
    )

    has_specify = True


class RadioSpecifyFixedOptions(OptionsFieldFormForRadioInputs):

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(field_num, *args, **kwargs)
        if isinstance(self.data, QueryDict):
            options = self.data.getlist("options")
        else:
            options = self.data["options"]

        # Options need to have been set as bound data on Form creation to work!
        options_choices = [(opt, opt) for opt in options]
        self.fields["specify_option"].choices = list(options_choices)

    specify_option = forms.ChoiceField(
        label=_("Specify Option"), widget=DropdownSelectForFieldForm()
    )

    has_specify = True
    can_add_options = False


class CheckboxFieldWithSpecifyForm(OptionsFieldFormForCheckboxes):

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
        label=_("Specify Option"), widget=DropdownSelectForFieldForm()
    )

    has_specify = True
