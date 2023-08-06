from django.test import TestCase
from django.contrib.auth.models import User
from buildings.models.models import Building

class BuildingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.building = Building.objects.create(
            street_number=1,
            street_name = "street",
            region = "montreal",
            province = "QC",
            country = "Canada",
            postal_code = "abcdef",
            formatted_address = "1 street ",
            cubf = 7417,
            lat = 23.545,
            lon = 46.4534,
        )
        self.typology = Typology.objects.create(name = 'prefab_metal')

    def test_building_cubf_name(self):
        # Original CUBF
        self.assertEqual(self.building.cubf_name(), "Salle ou salon de quilles")

        # Non-mapped CUBF name
        self.building.cubf = 1234
        self.assertEqual(self.building.cubf_name(), "")





