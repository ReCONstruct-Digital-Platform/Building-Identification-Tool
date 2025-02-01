from django.test import TestCase
from buildings.models import Dataset, User, Survey
from buildings.models.newsurveys import DynamicSurveyForm

from .utils.test_query_utils_constants import *

from bs4 import BeautifulSoup


class SurveyTest(TestCase):

    def setUp(self):
        self.user_1 = User.objects.create_superuser(
            username="testuser", password="testpw"
        )
        self.user_2 = User.objects.create_superuser(
            username="testuser2", password="testpw"
        )
        self.user_3 = User.objects.create_superuser(
            username="testuser3", password="testpw"
        )

        self.dataset = Dataset.objects.create(
            name="test-dataset",
            description="test",
            created_by=self.user_1,
            schema=dataset_schema,
        )

        self.survey1 = Survey.objects.create(
            name="test-dynamic-surveys",
            description="test-dynamic-surveys",
            dataset=self.dataset,
            created_by=self.user_1,
            schema=survey_schema,
        )

    def test_multi_checkbox_specify(self):

        schema = {
            "q1": {
                "pos": 0,
                "type": "text",
                "label": {"en": "Q1"},
                "question_text": {"en": "Test"},
                "widget": "multi_checkbox_specify",
                "widget_config": {
                    "specify_input_type": "text",
                    "specify_option_value": "a3",
                },
                "options": [
                    {"val": "a1", "label": {"en": "a1"}, "pos": 0},
                    {
                        "val": "a2",
                        "label": {"en": "a2"},
                        "pos": 1,
                    },
                    {"val": "a3", "label": {"en": "a3"}, "pos": 4},
                ],
            },
        }
        survey = Survey.objects.create(
            name="test-dynamic-surveys",
            description="test-dynamic-surveys",
            dataset=self.dataset,
            created_by=self.user_1,
            schema=schema,
        )

        data = {"q1": ["a1", "blablabla"]}

        form = DynamicSurveyForm(survey, data)

        assert len(schema.keys()) == len(form.fields)

        soup = BeautifulSoup(form.as_div(), "lxml")

        # a1 and a3 checkboxes should be checked
        # There should be text in the specify input
        assert "checked" in soup.find(id="id_q1_0").attrs
        assert "checked" not in soup.find(id="id_q1_1").attrs
        assert "checked" in soup.find(id="id_q1_specify").attrs
        assert "blablabla" == soup.find(id="id_q1_specify_value").attrs["value"]

    # TODO: test interger or null with both base data, radio
