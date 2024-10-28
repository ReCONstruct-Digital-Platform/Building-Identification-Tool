import code
from http import HTTPStatus
from django.test import TestCase, Client
from buildings.models.models import User, EvalUnit
from allauth.account.models import EmailAddress


class LoginViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser", password="testpw", email="test@email.com"
        )
        cls.user.save()
        cls.user.is_active = True
        cls.user.save()

        new_email_address = EmailAddress(
            user_id=cls.user.id,
            email=cls.user.email,
            verified=True,
            primary=True,
        )
        new_email_address.save()

        cls.eval_unit = EvalUnit.objects.create(
            id="id1",
            lat=1.0,
            lng=1.5,
            muni="mtl",
            year=2005,
            address="123 a st",
            mat18="fsd",
            cubf=1000,
            associated={"hlm": ["hlm1"]},
        )
        cls.eval_unit2 = EvalUnit.objects.create(
            id="id2",
            lat=1.0,
            lng=1.5,
            muni="mtl",
            year=2005,
            address="123 a st",
            mat18="fsd",
            cubf=1000,
            associated={"hlm": ["hlm1"]},
        )
        cls.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get("/", follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_redirect_if_not_logged_in_survey(self):
        response = self.client.get("/survey", follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        print(
            f"test_redirect_if_not_logged_in_survey redirect_chain: {response.redirect_chain}"
        )

        self.assertRedirects(
            response,
            "/accounts/login/?next=/survey/",
            status_code=301,
            target_status_code=200,
        )

    def test_logging_in_and_redirecting_to_survey(self):
        response = self.client.post(
            "/accounts/login?next=/survey",
            data={"username": "testuser", "password": "testpw"},
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        url, status = response.redirect_chain[0]
        self.assertEqual(url, "/accounts/login/?next=/survey")
        self.assertEqual(status, 301)


class SurveyViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="testpw")
        cls.eval_unit = EvalUnit.objects.create(
            id="id1",
            lat=1.0,
            lng=1.5,
            muni="mtl",
            year=2005,
            address="123 a st",
            mat18="fsd",
            cubf=1000,
            associated={"hlm": ["hlm1"]},
        )
        cls.eval_unit2 = EvalUnit.objects.create(
            id="id2",
            lat=1.0,
            lng=1.5,
            muni="mtl",
            year=2005,
            address="123 a st",
            mat18="fsd",
            cubf=1000,
            associated={"hlm": ["hlm1"]},
        )
        cls.client = Client()

    def test_get_survey_home(self):
        self.client.login(username="testuser", password="testpw")
        response = self.client.get("/survey", follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect_chain = response.redirect_chain

        print(f"test_get_survey_home redirect_chain: {redirect_chain}")
        self.assertEqual(len(redirect_chain), 2)

        url, status = redirect_chain[0]
        self.assertEqual(status, 301)
        self.assertRegex(url, r"/survey/")

        url, status = redirect_chain[1]
        self.assertEqual(status, 302)
        self.assertRegex(url, r"/survey/v1/id[12]")

    def test_get_survey_v1_specific(self):
        self.client.login(username="testuser", password="testpw")
        response = self.client.get("/survey/v1/id1", follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertListEqual(response.redirect_chain, [])
        self.assertEqual(response.context["eval_unit"], self.eval_unit)
