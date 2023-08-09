import os
import code
import subprocess

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from buildings.models.models import User, EvalUnit
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class MySeleniumTests(StaticLiveServerTestCase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        svc = Service(log_output=os.devnull)
        cls.s = WebDriver(service = svc)
        cls.w = WebDriverWait(cls.s, 10)
        cls.s.implicitly_wait(10)
        cls.user = User.objects.create_superuser(username='testuser', password='testpw')
        cls.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        

    @classmethod
    def tearDownClass(cls):
        cls.s.quit()
        super().tearDownClass()

    def test_login_to_survey(self):
        self.s.get(f"{self.live_server_url}/login?next=/survey")
        username_input = self.s.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = self.s.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        self.s.find_element(By.XPATH, '//input[@value="Login"]').click()
        self.w.until(EC.url_to_be(f"{self.live_server_url}/survey/v1/id1"))

    
