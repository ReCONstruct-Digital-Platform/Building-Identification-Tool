from django.test import TestCase
from django.db.models import Q
from django.db.models.expressions import Value

from buildings.models.models import User
from buildings.models.newmodels import Building, Dataset
from buildings.utils.query_utils import DatasetQParser, SurveyQParser

from .test_query_utils_constants import *


# From https://jamescooke.info/comparing-django-q-objects-in-python-3-with-pytest.html
def assert_q_equal(left, right):
    assert isinstance(left, Q), f"{left.__class__} is not subclass of Q"
    assert isinstance(right, Q), f"{right.__class__} is not subclass of Q"
    assert str(left) == str(right), f"Q{left} != Q{right}"


class DatasetQParserTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="testuser", password="testpw"
        )
        self.dataset_q_parser = DatasetQParser(schema=dataset_schema)

        self.dataset = Dataset.objects.create(
            name="test-dataset",
            description="test",
            created_by=self.user,
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

        self.expected_q_1 = Q(const_year__range=(1950, 2000)) & (
            Q(num_floors__gt=1) | Q(attrs__phys_link__in=["semi-detached", "row house"])
        )

    def test_query_builder_parser(self):

        result_q = self.dataset_q_parser.parse_query(dataset_query_1)
        assert_q_equal(result_q, self.expected_q_1)

        buildings = Building.objects.filter(result_q)

        assert self.building_1 in buildings
        assert self.building_2 in buildings

    def test_query_builder_parser_from_query(self):

        result_q = self.dataset_q_parser.parse_query(dataset_query_1["query"])
        assert_q_equal(result_q, self.expected_q_1)

        buildings = Building.objects.filter(result_q)

        assert self.building_1 in buildings
        assert self.building_2 in buildings

    def test_should_parse_null_input(self):
        result_q = self.dataset_q_parser.parse_query(None)
        expected_q = Q()

        assert_q_equal(result_q, expected_q)

    def test_is_null_operator(self):
        dataset_query_null = {
            "query": {
                "condition": "AND",
                "rules": [
                    {
                        "id": "attrs__phys_link",
                        "field": "attrs__phys_link",
                        "type": "string",
                        "input": "checkbox",
                        "operator": "is_null",
                        "value": "",
                    },
                ],
                "valid": True,
            }
        }
        result_q = self.dataset_q_parser.parse_query(dataset_query_null)

        expected_q = Q(attrs__phys_link=Value("null"))
        assert_q_equal(result_q, expected_q)

        buildings = Building.objects.filter(result_q)

        assert self.building_4 in buildings


class SurveyQParserTest(TestCase):

    def setUp(self):
        self.survey_q_parser = SurveyQParser()

    def test_survey_q_parser_1(self):
        self.survey_query_1 = {
            "condition": "AND",
            "rules": [
                {
                    "id": "s_1_exterior_cladding",
                    "field": "s_1_exterior_cladding",
                    "type": "string",
                    "input": "checkbox",
                    "operator": "in",
                    "value": ["brick_masonry", "wood"],
                },
                {
                    "id": "s_1_has_basement",
                    "field": "s_1_has_basement",
                    "type": "boolean",
                    "input": "checkbox",
                    "operator": "is_null",
                    "value": None,
                },
                {
                    "id": "s_2_num_storeys",
                    "field": "s_2_num_storeys",
                    "type": "integer",
                    "input": "number",
                    "operator": "between",
                    "value": [5, 8],
                },
            ],
            "valid": True,
        }
        result_q = self.survey_q_parser.parse_query(self.survey_query_1)
        expected_q = (
            Q(response_data__s_1_exterior_cladding__any_str_in=["brick_masonry", "wood"]) &
            Q(response_data__s_1_has_basement__contains=Value('null')) &
            Q(response_data__s_2_num_storeys__any_int_range=[5,8])
		)
        assert_q_equal(result_q, expected_q)
        
    def test_survey_q_parser_2(self):
        self.survey_query_2 = {
            "condition": "AND",
            "rules": [
                {
                    "id": "s_1_exterior_cladding",
                    "field": "s_1_exterior_cladding",
                    "type": "string",
                    "input": "checkbox",
                    "operator": "contains",
                    "value": "wood",
                },
                {
                    "condition": "OR",
                    "rules": [
						{
						"id": "s_1_has_basement",
						"field": "s_1_has_basement",
						"type": "boolean",
						"input": "checkbox",
						"operator": "in",
						"value": True,
					},
					{
						"id": "s_2_num_storeys",
						"field": "s_2_num_storeys",
						"type": "integer",
						"input": "number",
						"operator": "not_equal",
						"value": 5,
					},
                        
					]
				}
            ],
            "valid": True,
        }
        result_q = self.survey_q_parser.parse_query(self.survey_query_2)
        expected_q = (
            Q(response_data__s_1_exterior_cladding__any_str_like="%wood%") &
            (
                Q(response_data__s_1_has_basement__contains=True) |
            	~Q(response_data__s_2_num_storeys__any_int=5)
			)
		)
        assert_q_equal(result_q, expected_q)
        
    # def test_survey_q_parser_integer_operators(self):
    #     survey_query = {
    #         "condition": "AND",
    #         "rules": [
    #             {
    #                 "id": "f1",
    #                 "field": "f1",
    #                 "type": "integer",
    #                 "input": "number",
    #                 "operator": "equal",
    #                 "value": 2,
    #             },
    #             {
    #                 "condition": "OR",
    #                 "rules": [
	# 					{
	# 					"id": "s_1_has_basement",
	# 					"field": "s_1_has_basement",
	# 					"type": "boolean",
	# 					"input": "checkbox",
	# 					"operator": "in",
	# 					"value": True,
	# 				},
	# 				{
	# 					"id": "s_2_num_storeys",
	# 					"field": "s_2_num_storeys",
	# 					"type": "integer",
	# 					"input": "number",
	# 					"operator": "not_equal",
	# 					"value": 5,
	# 				},
                        
	# 				]
	# 			}
    #         ],
    #         "valid": True,
    #     }
    #     result_q = self.survey_q_parser.parse_query(survey_query)
    #     expected_q = (
    #         Q(response_data__s_1_exterior_cladding__any_str_like="%wood%") &
    #         (
    #             Q(response_data__s_1_has_basement__contains=True) |
    #         	~Q(response_data__s_2_num_storeys__any_int=5)
	# 		)
	# 	)
    #     assert_q_equal(result_q, expected_q)
        
