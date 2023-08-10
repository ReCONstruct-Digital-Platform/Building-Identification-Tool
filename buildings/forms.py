from .models.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import TextInput, EmailInput, PasswordInput


class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2'
        ]
        widgets = {
            'username': TextInput(attrs={'class': 'form-control', 'placeholder': 'Username...'}),
            'email': EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email...'}),
            'password1': PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password...'}),
            'password2': PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password...'}),
        }
