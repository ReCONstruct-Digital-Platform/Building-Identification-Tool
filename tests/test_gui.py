import os
import re

from django.test import Client
from selenium.webdriver.common.by import By
from selenium.webdriver import firefox, chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from buildings.models.models import User, EvalUnit
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class SeleniumFirefoxAndChromeTests(StaticLiveServerTestCase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        firefox_opts = firefox.options.Options()
        firefox_opts.add_argument('--headless')
        firefox_svc = firefox.service.Service(log_output=os.devnull)
        firefox_driver = firefox.webdriver.WebDriver(service = firefox_svc, options=firefox_opts)
        firefox_driver.implicitly_wait(10)

        chrome_opts = chrome.options.Options()
        chrome_opts.add_argument('--headless')
        chrome_svc = chrome.service.Service(log_output=os.devnull)
        chrome_driver = chrome.webdriver.WebDriver(service = chrome_svc, options=chrome_opts)
        chrome_driver.implicitly_wait(10)
        
        # Hold a driver for each browser
        cls.drivers = [(firefox_driver, WebDriverWait(firefox_driver, 10)),
                        (chrome_driver, WebDriverWait(chrome_driver, 10))]

        # Create DB objects
        cls.user = User.objects.create_superuser(username='testuser', password='testpw')
        cls.eval_unit = EvalUnit.objects.create(id='id1', lat=46.7879814932, lng=-71.2895307544, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        cls.eval_unit2 = EvalUnit.objects.create(id='id2', lat=46.7879814932, lng=-71.2895307544, muni='mtl', address='123 a st', mat18='fsd', cubf=1000)
        

    @classmethod
    def tearDownClass(cls):
        for driver, _ in cls.drivers:
            driver.quit()
        super().tearDownClass()



    def test_submit_survey(self):

        for driver, wait in self.drivers:

            driver.get(f"{self.live_server_url}/login?next=/survey")
            username_input = driver.find_element(By.NAME, "username")
            username_input.send_keys("testuser")
            password_input = driver.find_element(By.NAME, "password")
            password_input.send_keys("testpw")
            driver.find_element(By.XPATH, '//input[@value="Login"]').click()
            # Test redirect to an eval unit
            wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

            driver.get(f"{self.live_server_url}/survey/v1/id1")
            driver.find_element(By.ID, "nav-survey-tab").click()

            # Check the satellite screenshot was taken
            sat_data = driver.find_element(By.ID, "sat_data")
            self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64,')

            m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
            eval_unit_id = m.group(1)
            print(eval_unit_id)                    

            if eval_unit_id == 1:
                next_eval_unit_id = 2
            else:
                next_eval_unit_id = 1

            # Fill in the form
            driver.find_element(By.ID, "id_has_simple_footprint_0").click()
            driver.find_element(By.ID, "id_has_simple_volume_1").click()
            driver.find_element(By.ID, "id_num_storeys_specify").click()
            driver.find_element(By.ID, "id_num_storeys_specify_value").send_keys('5')
            driver.find_element(By.ID, "id_has_basement_2").click()
            driver.find_element(By.ID, "id_site_obstructions_0").click()
            driver.find_element(By.ID, "id_appendages_specify").click()
            driver.find_element(By.ID, "id_appendages_specify_value").send_keys('blabla')
            driver.find_element(By.ID, "id_exterior_cladding_5").click()
            driver.find_element(By.ID, "id_facade_condition_0").click()
            driver.find_element(By.ID, "id_window_wall_ratio_2").click()
            driver.find_element(By.ID, "id_large_irregular_windows_0").click()
            driver.find_element(By.ID, "id_roof_geometry_3").click()
            driver.find_element(By.ID, "id_structure_type_specify").click()
            driver.find_element(By.ID, "id_structure_type_specify_value").send_keys('struct type')

            # Submit the form
            driver.find_element(By.ID, "btn-submit-vote").click()

            wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{next_eval_unit_id}"))


