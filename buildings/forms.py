import json
from allauth.account.forms import AddEmailForm
from django import forms
from django.forms import widgets
from django.forms import Select, ChoiceField
from django.utils.translation import gettext_lazy as _
from allauth.account import forms as allauth_forms

from buildings.newwidgets import TestDragListWidget
from config.settings import DEBUG

TW_INPUT_CLASSES = """block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""

TW_INPUT_CHECKBOX_CLASSES = """block rounded-sm border-0 text-teal-600 accent-teal-600 focus:accent-teal-700 shadow-sm ring-1 focus:ring-2 focus:ring-teal-600 sm:text-sm sm:leading-6"""

KNOWLEDGE_LEVEL_CHOICES = (
    ("none", _("None")),
    ("student", _("AEC student")),
    ("professional", _("AEC professional")),
    ("other", _("Other")),
)


class BaseNewFieldForm(forms.Form):
    TW_CLASSES = """w-1/2 rounded-md text-lg border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = self.TW_CLASSES

    field_label = forms.CharField(
        label=_("Field Label"),
        initial="Field Label",
        max_length=100,
    )
    question_text = forms.CharField(
        label=_("Question Text"),
        max_length=500,
        widget=widgets.Textarea(attrs={"rows": 3}),
    )


class ListField(forms.Field):

    def to_python(self, value):
        super().to_python(value)
        if isinstance(value, str):
            return json.loads(value)
        return value

    def prepare_value(self, value):
        # Don't cast to string, we want it as a list for template rendering
        return value


class TrueFalseFieldForm(BaseNewFieldForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["options"].widget.attrs[
            "class"
        ] = """rounded-md text-lg border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600 sm:text-sm sm:leading-6"""

    options = ListField(label=_("Options"), widget=TestDragListWidget())


class LoginUserForm(allauth_forms.LoginForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["remember"].label = _("Remember me")
        self.fields["remember"].widget.attrs["class"] = TW_INPUT_CHECKBOX_CLASSES


class CreateUserForm(allauth_forms.SignupForm):

    knowledge_level = ChoiceField(
        choices=KNOWLEDGE_LEVEL_CHOICES,
        widget=Select(attrs={"class": TW_INPUT_CLASSES}),
        label=_("Level of Architecture, Engineering and Construction (AEC) knowledge"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Need to modify the password fields here instead of in Meta class below
        self.fields["email"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["username"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password1"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password1"].widget.attrs["minlength"] = 8
        self.fields["password2"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password2"].label = _("Confirm password")


class PasswordResetForm(allauth_forms.ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Need to modify the password fields here instead of in Meta class below
        self.fields["email"].widget.attrs["class"] = TW_INPUT_CLASSES


class ResetPasswordKeyForm(allauth_forms.ResetPasswordKeyForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Need to modify the password fields here instead of in Meta class below
        self.fields["password1"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password1"].widget.attrs["minlength"] = 8
        self.fields["password2"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

class ChangePasswordForm(allauth_forms.ChangePasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Need to modify the password fields here instead of in Meta class below
        self.fields["oldpassword"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["oldpassword"].widget.attrs["autocomplete"] = "off"
        self.fields["password1"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password1"].widget.attrs["minlength"] = 8 if not DEBUG else 2
        self.fields["password2"].widget.attrs["class"] = TW_INPUT_CLASSES
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

class ChangeEmailForm(AddEmailForm):
    def __init__(self, *args, **kwargs):
        super(AddEmailForm, self).__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["class"] = TW_INPUT_CLASSES
