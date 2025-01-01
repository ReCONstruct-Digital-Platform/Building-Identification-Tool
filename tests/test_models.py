from django.test import TestCase
from buildings.models import Dataset, User, Building, Response, Survey

from utils.test_query_utils_constants import *

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

        self.building_1 = Building.objects.create(
            address="test test",
            dataset=self.dataset,
            const_year=1956,
            num_floors=2,
            attrs={
                "phys_link": "other physical link",
            },
        )
        self.building_2 = Building.objects.create(
            address="test2",
            dataset=self.dataset,
            const_year=1975,
            num_floors=1,
            attrs={
                "phys_link": "semi-detached",
            },
        )
        self.building_3 = Building.objects.create(
            address="test3",
            dataset=self.dataset,
            const_year=2010,  # outside range
            num_floors=4,
            attrs={
                "phys_link": "semi-detached",
            },
        )
        self.building_4 = Building.objects.create(
            address="test3",
            dataset=self.dataset,
            const_year=2010,  # outside range
            num_floors=4,
            attrs={
                "phys_link": None,
            },
        )

        self.survey_1 = Survey.objects.create(
            name="test",
            description="test",
            dataset=self.dataset,
            created_by=self.user_1,
            schema=survey_schema,
            # survey 1's target population is building 1, 2 and 3
            dataset_filter={
                "rules": [
                    {
                        "field": "attrs__phys_link",
                        "value": ["semi-detached", "other physical link"],
                        "operator": "in",
                    }
                ],
                "condition": "AND",
            },
        )
        # A subsurvey on results of survey 1
        # It's target population should be only building 1
        self.survey_2 = Survey.objects.create(
            name="test2",
            description="test",
            dataset=self.dataset,
            created_by=self.user_1,
            schema=survey_schema,
            surveys_filter={
                "rules": [
                    {
                        # Should become a contains operator
                        "id": f"s_{self.survey_1.id}_appendages",
                        "field": f"s_{self.survey_1.id}_appendages",
                        "value": ["balconies"],
                        "type": "string",
                        "operator": "in",
                    },
                    {
                        "id":  f"s_{self.survey_1.id}_num_storeys",
                        "field":  f"s_{self.survey_1.id}_num_storeys",
                        "value": 2,
                        "type": "integer",
                        "operator": "greater",
                    },
                ],
                "condition": "AND",
            },
        )

        # A subsurvey on results of survey 1
        # It's target population should be only building 2
        self.survey_3 = Survey.objects.create(
            name="test2",
            description="test",
            dataset=self.dataset,
            created_by=self.user_1,
            schema=survey_schema,
            surveys_filter={
                "rules": [
                    {
                        # Should become a contains operator
                        "id": f"s_{self.survey_1.id}_appendages",
                        "field": f"s_{self.survey_1.id}_appendages",
                        "value": "balc",
                        "type": "string",
                        "operator": "contains",
                    },
                    {
                        "id": f"s_{self.survey_1.id}_has_basement",
                        "field": f"s_{self.survey_1.id}_has_basement",
                        "value": None,
                        "type": "string",
                        "operator": "is_null",
                    },
                    {
                        "id": f"s_{self.survey_1.id}_new_or_renovated",
                        "field": f"s_{self.survey_1.id}_new_or_renovated",
                        "value": True,
                        "type": "boolean",
                        "operator": "in",
                    },
                ],
                "condition": "AND",
            },
        )

        self.s1_r1 = Response.objects.create(
            building=self.building_1,
            survey=self.survey_1,
            created_by=self.user_1,
            data={
                "appendages": ["balconies", "porches_stoops"],
                "num_storeys": 3,
                "has_basement": True,
                "new_or_renovated": None,
            },
        )

        self.s1_r2 = Response.objects.create(
            building=self.building_1,
            survey=self.survey_1,
            created_by=self.user_2,
            data={
                "appendages": ["random_stuff"],
                "num_storeys": 4,
                "has_basement": None,
                "new_or_renovated": True,
            },
        )

        self.s1_r3 = Response.objects.create(
            building=self.building_2,
            survey=self.survey_1,
            created_by=self.user_1,
            data={
                "appendages": ["balconies", "random_stuff"],
                "num_storeys": 2,
                "has_basement": None,
                "new_or_renovated": True,
            },
        )

        self.survey_query_1 = {
            "condition": "AND",
            "rules": [
                {
                    "id": "s_5_exterior_cladding",
                    "field": "s_5_exterior_cladding",
                    "type": "string",
                    "input": "checkbox",
                    "operator": "in",
                    "value": ["brick_masonry", "wood"],
                },
                {
                    "id": "s_5_has_basement",
                    "field": "s_5_has_basement",
                    "type": "boolean",
                    "input": "checkbox",
                    "operator": "is_null",
                    "value": None,
                },
                {
                    "id": "s_6_num_storeys",
                    "field": "s_6_num_storeys",
                    "type": "integer",
                    "input": "number",
                    "operator": "between",
                    "value": [5, 8],
                },
            ],
            "valid": True,
        }

    def test_survey_target_population(self):

      buildings = self.survey_1.get_target_population()

      assert self.building_1 in buildings
      assert self.building_2 in buildings
      assert self.building_3 in buildings

    def test_survey_target_population_subsurvey_1(self):

      buildings = self.survey_2.get_target_population()

      print(buildings)

      assert self.building_1 in buildings

    def test_survey_target_population_subsurvey_2(self):

      buildings = self.survey_3.get_target_population()
      print(buildings)

      assert self.building_2 in buildings
