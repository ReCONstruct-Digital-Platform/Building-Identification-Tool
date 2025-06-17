import autocomplete
from django import forms
from django.core.validators import RegexValidator
from django.utils import timezone
from buildings.models.newmodels import DatasetOnboardingJob
from buildings.models.newsurveys import MyJSONField
from buildings.forms import TW_INPUT_CLASSES
from buildings.widgets.newwidgets import TW_RADIO_CLASS


UPLOAD_FILE_CLASSES = """block w-full rounded-md py-1.5 text-gray-900 shadow-sm placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600"""


class DatasetOnboardingForm(forms.ModelForm):

    # New fields for CSV upload
    csv_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"class": UPLOAD_FILE_CLASSES, "accept": ".csv"}),
    )

    address_column = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    state_column = forms.CharField(
        required=False,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            }
        ),
    )

    zip_column = forms.CharField(
        required=False,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            }
        ),
    )

    class Meta:
        model = DatasetOnboardingJob
        fields = ['name', 'description']
        widgets = {
            "name": forms.TextInput(attrs={"class": TW_INPUT_CLASSES}),
            "description": forms.Textarea(attrs={"class": TW_INPUT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


    def clean(self):
        cleaned_data = super().clean()

        # Do validation on multiple fields

        return cleaned_data
