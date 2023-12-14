from .models.models import User
from django.utils.translation import gettext_lazy as _
from django.forms import TextInput, EmailInput, Select, ChoiceField
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


TW_INPUT_CLASSES = """block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 
    ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset 
    focus:ring-teal-600 sm:text-sm sm:leading-6"""

KNOWLEDGE_LEVEL_CHOICES = (
    ('none', 'None'),
    ('student', 'AEC student'),
    ('professional', 'AEC professional'),
    ('other', 'Other')
)


class LoginUserForm(AuthenticationForm):
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password'].widget.attrs['class'] = TW_INPUT_CLASSES


class CreateUserForm(UserCreationForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Need to modify the password fields here instead of in Meta class below
        self.fields['password1'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password1'].widget.attrs['minlength'] = 8
        self.fields['password2'].widget.attrs['class'] = TW_INPUT_CLASSES
        self.fields['password2'].label = _("Confirm password")

    knowledge_level = ChoiceField(
        choices=KNOWLEDGE_LEVEL_CHOICES,
        widget=Select(attrs={'class': TW_INPUT_CLASSES}),
        label=_("Level of Architecture, Engineering and Contruction (AEC) knowledge"),
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'knowledge_level'
        ]
        widgets = {
            'username': TextInput(attrs={'class': TW_INPUT_CLASSES, 'autocomplete': 'username', 'minlength': 3}),
            'email': EmailInput(attrs={'class': TW_INPUT_CLASSES, 'autocomplete': 'email', 'required': True}),
        }
