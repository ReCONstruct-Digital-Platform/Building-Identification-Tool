import json
from django import forms
from django.forms import NullBooleanField, widgets
from buildings.newwidgets import RadioSelect, RadioSelectForFieldForm
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
    TW_CLASSES = """rounded-md text-lg border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.field_num = field_num

    field_label = forms.CharField(
        label=_("Field Label"),
        initial="Field Label",
        max_length=100,
        widget=TextInputWidget(attrs={"class": TW_CLASSES}),
    )
    question_text = forms.CharField(
        label=_("Question Text"),
        max_length=500,
        widget=TextAreaWidget(attrs={"rows": 2, "class": TW_CLASSES}),
    )


class OptionsFieldForm(BaseNewFieldForm):

    OPTIONS_CLASSES = """rounded-md text-lg border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""

    def __init__(self, field_num, *args, **kwargs):
        super().__init__(field_num, *args, **kwargs)

    can_add_options = False

    options = ListField(
        label=_("Options"), widget=DragListWidget(attrs={"class": OPTIONS_CLASSES})
    )


class OptionsFieldFormWithSpecify(OptionsFieldForm):

    num_columns = forms.ChoiceField(
        label=_("Num Columns"),
        widget=RadioSelectForFieldForm(
            attrs={"class": "grid grid-cols-3 gap-2"},
        ),
        choices=((1, _("1")), (2, _("2")), (3, _("3"))),
        initial=1,
    )

    can_add_options = True

    # has_specify = forms.ChoiceField(
    #     label=_("Has Specify?"),
    #     widget=RadioSelectForFieldForm(
    #         attrs={"class": "flex flex-row gap-2"},
    #     ),
    #     choices=((False, _("No")), (True, _("Yes"))),
    #     initial=False,
    # )
