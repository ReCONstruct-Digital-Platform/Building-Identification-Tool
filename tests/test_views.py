import code
from http import HTTPStatus
from django.test import TestCase, Client
from buildings.models.models import User, EvalUnit


class LoginViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='testpw')
        cls.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        cls.eval_unit2 = EvalUnit.objects.create(id='id2', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        cls.client = Client()
        
    def test_redirect_if_not_logged_in(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, '/login?next=/')

    def test_redirect_if_not_logged_in_survey(self):
        response = self.client.get("/survey")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, '/login?next=/survey')

    def test_logging_in_and_redirecting_to_survey(self):
        response = self.client.post('/login?next=/survey', data={'username':'testuser', 'password':'testpw'}, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        url, status =  response.redirect_chain[0]
        self.assertEqual(url, '/survey')
        self.assertEqual(status, 302)

        url, status =  response.redirect_chain[1]
        self.assertRegex(url, r'/survey/v1/id[12]')
        self.assertEqual(status, 302)



class SurveyViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='testpw')
        cls.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        cls.eval_unit2 = EvalUnit.objects.create(id='id2', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        cls.client = Client()

    def test_get_survey_home(self):
        self.client.login(username='testuser', password='testpw')
        response = self.client.get("/survey", follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect_chain = response.redirect_chain
        self.assertEqual(len(redirect_chain), 1)
        url, status = redirect_chain[0]
        self.assertEqual(status, 302)
        self.assertRegex(url, r'/survey/v1/id[12]')

    def test_get_survey_v1_specific(self):
        self.client.login(username='testuser', password='testpw')
        response = self.client.get("/survey/v1/id1", follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertListEqual(response.redirect_chain, [])
        self.assertEqual(response.context['eval_unit'], self.eval_unit)