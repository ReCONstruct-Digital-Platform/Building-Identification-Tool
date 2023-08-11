from django.test import TestCase
from buildings.models.models import EvalUnit, User, Vote

class EvalUnitTestCase(TestCase):
    serialized_rollback = False

    def setUp(self):
        self.user = User.objects.create_superuser(username='testuser', password='testpw')
        self.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        self.eval_unit2 = EvalUnit.objects.create(id='id2', lat=1.0, lng=1.5, muni='mtl', address='4656 a st', mat18='fsdfsd', cubf=1000)
 

    def test_cubf_name(self):
        # Original CUBF
        self.assertEqual(self.eval_unit.cubf_name(), "Residential")

        # Non-mapped CUBF name
        self.eval_unit.cubf = 1234
        self.assertEqual(self.eval_unit.cubf_name(), "")


    def test_get_next_evalunit_to_vote(self):
        # create a new vote on the first eval unit
        Vote.objects.create(eval_unit = self.eval_unit, user = self.user)
        
        # Now we should get the other as the next to vote on
        eu = EvalUnit.objects.get_next_unit_to_survey(id_only=True)
        self.assertEqual(eu, self.eval_unit2.id)

        # vote on the second one twice
        Vote.objects.create(eval_unit = self.eval_unit2, user = self.user)
        Vote.objects.create(eval_unit = self.eval_unit2, user = self.user)

        # Now it should return the least voted one, the first
        eu = EvalUnit.objects.get_next_unit_to_survey(id_only=True)
        self.assertEqual(eu, self.eval_unit.id)

        # Now if we exlcude id1, it should give us id2
        eu = EvalUnit.objects.get_next_unit_to_survey(id_only=True, exclude_id='id1')
        self.assertEqual(eu, self.eval_unit2.id)