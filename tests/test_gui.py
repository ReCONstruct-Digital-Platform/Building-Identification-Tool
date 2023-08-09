import os
import code

from selenium.webdriver.common.by import By
from selenium.webdriver import firefox, chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from buildings.models.models import User, EvalUnit
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class SeleniumFirefoxTests(StaticLiveServerTestCase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = firefox.options.Options()
        opts.add_argument('--headless')
        svc = firefox.service.Service(log_output=os.devnull)
        cls.driver = firefox.webdriver.WebDriver(service = svc, options=opts)
        cls.wait = WebDriverWait(cls.driver, 10)
        cls.driver.implicitly_wait(10)
        cls.user = User.objects.create_superuser(username='testuser', password='testpw')
        cls.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()


    def test_login_to_survey(self):
        self.driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = self.driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        self.driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        self.wait.until(EC.url_to_be(f"{self.live_server_url}/survey/v1/id1"))

    
class SeleniumChromeTests(StaticLiveServerTestCase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = chrome.options.Options()
        opts.add_argument('--headless')
        svc = chrome.service.Service(log_output=os.devnull)
        cls.driver = chrome.webdriver.WebDriver(service = svc, options=opts)
        cls.wait = WebDriverWait(cls.driver, 10)
        cls.driver.implicitly_wait(10)
        cls.user = User.objects.create_superuser(username='testuser', password='testpw')
        cls.eval_unit = EvalUnit.objects.create(id='id1', lat=1.0, lng=1.5, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()


    def test_login_to_survey(self):
        self.driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = self.driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        self.driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        self.wait.until(EC.url_to_be(f"{self.live_server_url}/survey/v1/id1"))