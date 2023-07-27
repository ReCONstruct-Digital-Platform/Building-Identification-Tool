from django import forms
from django.forms.utils import ErrorList
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm, TextInput, EmailInput, PasswordInput

from buildings.models.surveys import SurveyV1


class SurveyV1Form(ModelForm):
    class Meta:
        model = SurveyV1
        fields = ["q1", "q2", "q3", "q4"]


class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2'
        ]
        widgets = {
            'username': TextInput(attrs={'class': 'form-control', 'placeholder': 'Username...'}),
            'email': EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password...'})
        self.fields['password2'].widget = PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password...'})

