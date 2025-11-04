from django import forms
from buildings.models.newmodels import DatasetOnboardingJob
from buildings.forms import TW_INPUT_CLASSES
from buildings.widgets.newwidgets import TW_RADIO_CLASS


UPLOAD_FILE_CLASSES = """block w-full rounded-md py-1.5 text-gray-900 shadow-sm placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600"""

# Data types for unmapped columns
COLUMN_DATA_TYPES = [
    ("string", "Text"),
    ("double", "Decimal Number"),
    ("integer", "Integer"),
    ("boolean", "Boolean"),
    ("date", "Date"),
]


class DatasetOnboardingForm(forms.ModelForm):

    # New fields for CSV upload
    csv_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"class": UPLOAD_FILE_CLASSES, "accept": ".csv"}),
    )

    external_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    address_column = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    # Street components
    street_name_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    street_num_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    street_num_2_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    # Location fields
    muni_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    submuni_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    state_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    zip_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    # Building characteristics
    const_year_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    num_floors_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    floor_area_column = forms.CharField(
        required=False,
        widget=forms.Select(attrs={"class": TW_INPUT_CLASSES}),
    )

    has_coordinates = forms.ChoiceField(
        required=True,
        choices=[(False, "No"), (True, "Yes")],
        initial=False,
        widget=forms.RadioSelect(attrs={"class": TW_RADIO_CLASS}),
    )

    lat_column = forms.CharField(
        required=False,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            }
        ),
    )

    lng_column = forms.CharField(
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

    # Field to store unmapped columns and their data types
    unmapped_columns = forms.JSONField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        # Do validation on multiple fields
        if cleaned_data.get("has_coordinates") is True:
            if not cleaned_data.get('lat_column'):
                self.add_error('lat_column', 'Latitude column is required when coordinates are provided')
            if not cleaned_data.get('lng_column'):
                self.add_error('lng_column', 'Longitude column is required when coordinates are provided')

        return cleaned_data
