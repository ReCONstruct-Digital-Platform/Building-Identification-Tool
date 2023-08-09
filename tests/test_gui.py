from django.test import TestCase
from django.contrib.auth.models import User

class MyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.foo = User.create_user(username='testuser', password='testpw')
        ...

    def test1(self):
        # Some test using self.foo
        ...
