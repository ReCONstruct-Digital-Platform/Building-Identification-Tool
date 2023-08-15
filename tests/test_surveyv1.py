from django.test import TestCase
from django.forms.models import model_to_dict
from buildings.models import SurveyV1Form, User, EvalUnit
from buildings.models.models import Vote


class MyTests(TestCase):

    serialized_rollback = False
    
    def setUp(self):
        self.user = User.objects.create_superuser(username='testuser', password='testpw')
        self.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000, associated={'hlm': ['hlm1']})
        self.eval_unit2 = EvalUnit.objects.create(id='id2', lat=1.0, lng=1.5, muni='mtl', address='4656 a st', mat18='fsdfsd', cubf=1000, associated={'hlm': ['hlm1']})
        self.form_data = {
            "has_simple_footprint": 'True',
            "has_simple_volume": 'False',
            "num_storeys": 5,
            "has_basement": '',
            "site_obstructions": ['trees_or_landscaping', 'buildings', 'on', 'specified'],
            "appendages": ['balconies', 'porches_stoops'],
            "exterior_cladding": ['concrete'],
            "facade_condition": 'good',
            "window_wall_ratio": 'unsure',
            "large_irregular_windows": 'False',
            "roof_geometry": 'flat',
            "structure_type": 'specified',
            "new_or_renovated": '',
        }

    def test_survey_v1_cleaning(self):
        form = SurveyV1Form(data=self.form_data)
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.cleaned_data, {
            "has_simple_footprint": True,
            "has_simple_volume": False,
            "num_storeys": 5,
            "has_basement": None,
            "site_obstructions": ['trees_or_landscaping', 'buildings', 'on', 'specified'],
            "appendages": ['balconies', 'porches_stoops'],
            "exterior_cladding": ['concrete'],
            "facade_condition": 'good',
            "window_wall_ratio": 'unsure',
            "large_irregular_windows": False,
            "roof_geometry": 'flat',
            "structure_type": 'specified',
            "new_or_renovated": None,   
        })

    def test_form_post_and_initial_fill(self):
        # Login and post a form
        self.client.login(username='testuser', password='testpw')
        response = self.client.post("/survey/v1/id1", data=self.form_data, follow=True)
        # Check we got redirected to the next eval unit
        self.assertListEqual(response.redirect_chain, [('/survey/v1/id2', 302)])

        # Now get the first page again, the form data should be loaded in
        response = self.client.get("/survey/v1/id1")
        self.assertTrue(response.context['form'].was_filled)
        form_as_dict = model_to_dict(response.context['form'].instance)
        # Get the current vote id
        # the PKs keep incrementing between tests, but objects get destroyed
        vote_id = Vote.objects.first().id
        self.assertDictEqual(form_as_dict, {
            "id": 1,
            "vote": vote_id,
            "has_simple_footprint": True,
            "has_simple_volume": False,
            "num_storeys": 5,
            "has_basement": None,
            "site_obstructions": ['trees_or_landscaping', 'buildings', 'on', 'specified'],
            "appendages": ['balconies', 'porches_stoops'],
            "exterior_cladding": ['concrete'],
            "facade_condition": 'good',
            "window_wall_ratio": 'unsure',
            "large_irregular_windows": False,
            "roof_geometry": 'flat',
            "structure_type": 'specified',
            "new_or_renovated": None,   
        })
