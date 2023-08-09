from django.test import TestCase
from django.contrib.auth.models import User
from buildings.models.models import EvalUnit

class EvalUnitTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.evalunit = EvalUnit.objects.create(
            id = "3fvsg",
            address = "1 street name",
            lat = 23.545,
            lng = 46.4534,
            cubf = 1000
        )

    def test_building_cubf_name(self):
        # Original CUBF
        self.assertEqual(self.evalunit.cubf_name(), "Residential")

        # Non-mapped CUBF name
        self.evalunit.cubf = 1234
        self.assertEqual(self.evalunit.cubf_name(), "")





