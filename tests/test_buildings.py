from django.test import TestCase
from django.contrib.auth.models import User
from buildings.models.models import EvalUnit

class BuildingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.building = EvalUnit.objects.create(
            id = "3fvsg",
            address = "1 street name",
            lat = 23.545,
            lon = 46.4534,
        )

    def test_building_cubf_name(self):
        # Original CUBF
        self.assertEqual(self.building.cubf_name(), "Salle ou salon de quilles")

        # Non-mapped CUBF name
        self.building.cubf = 1234
        self.assertEqual(self.building.cubf_name(), "")





