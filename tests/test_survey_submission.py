import os
import re
from django.urls import reverse
from django.test import tag
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from buildings.models import Dataset, User, Survey, Building
from allauth.account.models import EmailAddress
from tests.gui_tests_base import ChromeSeleniumTestsBase
from tests.utils.test_query_utils_constants import dataset_simple_schema


survey_schema = {
    "appendages": {
        "type": "text",
        "label": {"en": "Appendages"},
        "widget": "multi_checkbox_specify",
        "options": [
            {"val": "balconies", "label": {"en": "Balconies"}, "pos": 0},
            {
                "val": "vestibules",
                "label": {"en": "Exterior Vestibules"},
                "pos": 1,
            },
            {
                "val": "canopies_eaves",
                "label": {"en": "Roof overhangs/eaves"},
                "pos": 2,
            },
            {
                "val": "porches_stoops",
                "label": {"en": "Porches/stoops"},
                "pos": 3,
            },
            {"val": "other", "label": {"en": "Other (specify)"}, "pos": 4},
        ],
        "question_text": {
            "en": "Select any and all significant appendages to the building faces."
        },
        "widget_config": {
            "attrs": {"class": "survey-1col"},
            "specify_input_type": "text",
            "specify_option_value": "other",
        },
        "pos": 7,
    },
    "num_storeys": {
        "type": "integer",
        "label": {"en": "Number of Storeys"},
        "widget": "radio_w_specify",
        "options": [
            {
                "val": "num_storeys",
                "label": {"en": "Number of storeys"},
                "pos": 0,
            },
            {"val": None, "label": {"en": "Unsure"}, "pos": 1},
        ],
        "question_text": {
            "en": "How many storeys above-ground does the building have?"
        },
        "widget_config": {
            "attrs": {"class": "survey-1col"},
            "specify_input_type": "number",
            "specify_option_value": "num_storeys",
        },
        "pos": 4,
    },
}

@tag('selenium')
class SurveySubmissionTest(ChromeSeleniumTestsBase):
    """Test the survey submission view"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass(headless=False)

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_superuser(
            username="testuser",
            password="987mysupersecurepassword",
            email="testuser@example.com",
        )

        # Verify the user's email to bypass email verification
        email = EmailAddress.objects.get_or_create(
            user=self.user, email="testuser@example.com"
        )[0]
        email.verified = True
        email.primary = True
        email.save()

        # Create a dataset
        self.dataset = Dataset.objects.create(
            name="test-dataset",
            description="test dataset for survey submission",
            created_by=self.user,
            schema=dataset_simple_schema,
        )

        # Create a survey with ACTIVE status
        self.survey = Survey.objects.create(
            name="test-survey",
            description="test survey for submission",
            dataset=self.dataset,
            created_by=self.user,
            schema=survey_schema,
            status=Survey.Status.ACTIVE
        )

        # Create attrs dictionary with all required fields
        attrs = {
            "attr1": "",
            "attr2": "",
        }

        # Create two buildings with attrs initialized
        self.building1 = Building.objects.create(
            address="123 Test Street",
            muni="Test City",
            submuni="Test Neighborhood",
            dataset=self.dataset,
            lat=45.5017,
            lng=-73.5673,
            ext_id="test-building-1",
            attrs=attrs.copy(),  # Use copy to avoid sharing the same dict
        )

        self.building2 = Building.objects.create(
            address="456 Test Avenue",
            muni="Test City",
            submuni="Test Neighborhood",
            dataset=self.dataset,
            lat=45.5020,
            lng=-73.5680,
            ext_id="test-building-2",
            attrs=attrs.copy(),  # Use copy to avoid sharing the same dict
        )

    def test_survey_submission(self):
        """Test that a user can fill in and submit a survey"""
        # First, sign in to the application
        self._sign_in()

        # Get the survey URL
        survey_url = reverse('buildings:do_survey', kwargs={
            'survey_slug': self.survey.slug, 
            'building_slug': self.building1.slug
        })

        # Print the actual slugs for debugging
        print(f"Survey URL: {survey_url}")

        # Navigate directly to the survey page
        self.driver.get(f"{self.live_server_url}{survey_url}")

        # Print debugging information
        print(f"Current URL before filling form: {self.driver.current_url}")

        # Wait for the form to be fully loaded
        self.wait.until(
            EC.presence_of_element_located((By.ID, "building-submission-form"))
        )

        # Print all form elements for debugging
        form_elements = self.driver.find_elements(
            By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']"
        )
        print("Form elements:")
        for elem in form_elements[:10]:  # Print first 10 elements
            print(
                f"Name: {elem.get_attribute('name')}, Value: {elem.get_attribute('value')}"
            )

        # Fill in the form fields based on the survey schema

        # Appendages - select "Balconies"
        self.driver.find_element(
            By.CSS_SELECTOR, "input[name='appendages'][value='balconies']"
        ).click()

        # Select the specify option for appendages
        self.driver.find_element(By.ID, "id_num_storeys_specify").click()

        # Enter 2 storeys in the text box
        specify_number_box = self.driver.find_element(
            By.CSS_SELECTOR, "input[name='num_storeys'][type='number']"
        )
        self.wait.until(EC.element_to_be_clickable(specify_number_box))

        specify_number_box.send_keys("2")

        # Submit the form
        submit_button = self.driver.find_element(By.ID, "btn-submit-vote")
        submit_button.click()

        # Wait for the redirect to complete
        self.wait.until(EC.url_changes(self.driver.current_url))

        # After form submission, we should be redirected to the next building
        print(f"Current URL after form submission: {self.driver.current_url}")

        # Verify we're redirected to the next building
        current_url = self.driver.current_url
        expected_url = f"{self.live_server_url}{reverse('buildings:do_survey', kwargs={'survey_slug': self.survey.slug, 'building_slug': self.building2.slug})}"

        self.assertEqual(current_url, expected_url, 
                         f"Expected to be redirected to {expected_url}, but got {current_url}")

        # Verify a response was created for the first building
        self.assertEqual(self.building1.response_set.count(), 1, 
                         "Expected one response for building1")

        # Verify the response is associated with the correct survey and user
        response = self.building1.response_set.first()
        self.assertEqual(response.survey, self.survey, 
                         "Response should be associated with the correct survey")
        self.assertEqual(response.created_by, self.user, 
                         "Response should be associated with the correct user")
