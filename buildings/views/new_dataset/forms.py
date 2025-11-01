import autocomplete
from django import forms
from django.core.validators import RegexValidator
from django.utils import timezone
from buildings.models.newmodels import DatasetOnboardingJob
from buildings.models.newsurveys import MyJSONField
from buildings.forms import TW_INPUT_CLASSES
from buildings.widgets.newwidgets import TW_RADIO_CLASS


UPLOAD_FILE_CLASSES = """block w-full rounded-md py-1.5 text-gray-900 shadow-sm placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-teal-600"""

# Data types for unmapped columns
COLUMN_DATA_TYPES = [
    ('string', 'String'),
    ('number', 'Number'),
    ('boolean', 'Boolean'),
    ('date', 'Date'),
    ('array', 'Array'),
    ('object', 'Object')
]


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
        choices=[('no', 'No'), ('yes', 'Yes')],
        initial='no',
        widget=forms.RadioSelect(attrs={"class": TW_RADIO_CLASS}),
    )
    
    has_building_details = forms.ChoiceField(
        required=True,
        choices=[('no', 'No'), ('yes', 'Yes')],
        initial='no',
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
    self.user = kwargs.pop('user', None)
    super().__init__(*args, **kwargs)



    def clean(self):
        cleaned_data = super().clean()

        # Do validation on multiple fields
        if cleaned_data.get('has_coordinates') == 'yes':
            if not cleaned_data.get('lat_column'):
                self.add_error('lat_column', 'Latitude column is required when coordinates are provided')
            if not cleaned_data.get('lng_column'):
                self.add_error('lng_column', 'Longitude column is required when coordinates are provided')

        # Make postal code optional but recommended
        if not cleaned_data.get('zip_column'):
            # This is just a warning, not an error that prevents form submission
            self.add_error('zip_column', 'Postal code is recommended for better geocoding accuracy')
            
        # Validate building details fields if selected
        if cleaned_data.get('has_building_details') == 'yes':
            # These fields are optional but recommended when building details are enabled
            if not cleaned_data.get('const_year_column'):
                self.add_error('const_year_column', 'Construction year column is recommended for building details')
            if not cleaned_data.get('num_floors_column'):
                self.add_error('num_floors_column', 'Number of floors column is recommended for building details')
            if not cleaned_data.get('floor_area_column'):
                self.add_error('floor_area_column', 'Floor area column is recommended for building details')

        return cleaned_data
