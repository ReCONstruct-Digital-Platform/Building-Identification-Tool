from .models.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import TextInput, EmailInput, PasswordInput


class CreateUserForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['placeholder'] = 'Enter Password...'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password...'


    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2'
        ]
        widgets = {
            'username': TextInput(attrs={'class': 'form-control', 'placeholder': 'Username...'}),
            'email': EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email...'}),
        }
