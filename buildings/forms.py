from django.forms import Select, ChoiceField
from django.utils.translation import gettext_lazy as _
from allauth.account import forms as allauth_forms

TW_INPUT_CLASSES = """block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset 
    focus:ring-teal-600 sm:text-sm sm:leading-6"""

TW_INPUT_CHECKBOX_CLASSES = """block rounded-sm border-0 text-teal-600 accent-teal-600 focus:accent-teal-700 shadow-sm ring-1 focus:ring-2 focus:ring-teal-600 sm:text-sm sm:leading-6"""

KNOWLEDGE_LEVEL_CHOICES = (
    ('none', _('None')),
    ('student', _('AEC student')),
    ('professional', _('AEC professional')),
    ('other', _('Other'))
)


class LoginUserForm(allauth_forms.LoginForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['login'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['remember'].label = _("Remember me")
        self.fields['remember'].widget.attrs['class'] = TW_INPUT_CHECKBOX_CLASSES

class CreateUserForm(allauth_forms.SignupForm):
    
    knowledge_level = ChoiceField(
        choices=KNOWLEDGE_LEVEL_CHOICES,
        widget=Select(attrs={'class': TW_INPUT_CLASSES}),
        label=_("Level of Architecture, Engineering and Contruction (AEC) knowledge"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Need to modify the password fields here instead of in Meta class below
        self.fields['email'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['username'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password1'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password1'].widget.attrs['minlength'] = 8
        self.fields['password2'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password2'].label = _("Confirm password")


class PasswordResetForm(allauth_forms.ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Need to modify the password fields here instead of in Meta class below
        self.fields['email'].widget.attrs['class'] = TW_INPUT_CLASSES


class ResetPasswordKeyForm(allauth_forms.ResetPasswordKeyForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Need to modify the password fields here instead of in Meta class below
        self.fields['password1'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password1'].widget.attrs['minlength'] = 8
        self.fields['password2'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password' 
