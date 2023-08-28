import os
import re

from selenium.webdriver.common.by import By
from selenium.webdriver import firefox, chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class CommonSeleniumTestsBase(StaticLiveServerTestCase):
    """Common base class for Firefox and Chrome Selenium Tests"""

    def _sign_in(self, next_url='/', username='testuser', password='testpw'):
        self.driver.get(f"{self.live_server_url}/login?next={next_url}")
        username_input = self.driver.find_element(By.NAME, "username")
        username_input.send_keys(username)
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        self.driver.find_element(By.XPATH, '//input[@value="Login"]').click()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    def _get_next_eval_unit_id_when_there_are_2(self):
        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', self.driver.current_url)

        if m.group(1) == '1':
            return '2'
        else:
            return '1'

class ChromeSeleniumTestsBase(CommonSeleniumTestsBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        chrome_opts = chrome.options.Options()
        chrome_opts.add_argument('--headless')
        chrome_svc = chrome.service.Service(log_output=os.devnull)
        chrome_driver = chrome.webdriver.WebDriver(service = chrome_svc, options=chrome_opts)
        chrome_driver.implicitly_wait(10)

        cls.driver = chrome_driver
        cls.wait = WebDriverWait(chrome_driver, 10)


    def _submit_form(self):
        driver = self.driver
        wait = self.wait
        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Fill in the form
        # Chrome has a problem where it cant scroll normally like friefox
        # So we call a scroll into view on each element before clicking on them
        e = driver.find_element(By.ID, "id_has_simple_footprint_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_has_simple_volume_1")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_num_storeys_specify")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_num_storeys_specify_value")
        driver.execute_script("arguments[0].value = arguments[1];", e, '5')

        e = driver.find_element(By.ID, "id_has_basement_2")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_site_obstructions_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_appendages_specify")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_appendages_specify_value")
        driver.execute_script("arguments[0].value = arguments[1];", e, 'blabla')

        e = driver.find_element(By.ID, "id_exterior_cladding_5")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        
        e = driver.find_element(By.ID, "id_facade_condition_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_window_wall_ratio_2")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_large_irregular_windows_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_roof_geometry_3")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_structure_type_specify")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_structure_type_specify_value")
        driver.execute_script("arguments[0].value = arguments[1];", e, 'struct type')

        # Submit the form
        e = driver.find_element(By.ID, "btn-submit-vote")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Proxy to know when sat map is visible 
        # Do this to wait for next page load, else form might not submit properly
        wait.until(EC.visibility_of_element_located((By.ID, 'gmimap1')))



class FirefoxSeleniumTestsBase(CommonSeleniumTestsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        firefox_opts = firefox.options.Options()
        firefox_opts.add_argument('--headless')
        firefox_svc = firefox.service.Service(log_output=os.devnull)
        firefox_driver = firefox.webdriver.WebDriver(service = firefox_svc, options=firefox_opts)
        firefox_driver.implicitly_wait(10)

        # Hold a driver for each browser
        cls.driver = firefox_driver
        cls.wait = WebDriverWait(firefox_driver, 10)


    def _submit_form(self):
        """
        On a survey page, fills in a form and submits
        """
        self.wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        self.driver.find_element(By.ID, "nav-survey-tab").click()
        self.driver.find_element(By.ID, "id_has_simple_footprint_0").click()
        self.driver.find_element(By.ID, "id_has_simple_volume_1").click()
        self.driver.find_element(By.ID, "id_num_storeys_specify").click()
        self.driver.find_element(By.ID, "id_num_storeys_specify_value").send_keys('5')
        self.driver.find_element(By.ID, "id_has_basement_2").click()
        self.driver.find_element(By.ID, "id_site_obstructions_0").click()
        self.driver.find_element(By.ID, "id_appendages_specify").click()
        self.driver.find_element(By.ID, "id_appendages_specify_value").send_keys('blabla')
        self.driver.find_element(By.ID, "id_exterior_cladding_5").click()
        self.driver.find_element(By.ID, "id_facade_condition_0").click()
        self.driver.find_element(By.ID, "id_window_wall_ratio_2").click()
        self.driver.find_element(By.ID, "id_large_irregular_windows_0").click()
        self.driver.find_element(By.ID, "id_roof_geometry_3").click()
        self.driver.find_element(By.ID, "id_structure_type_specify").click()
        self.driver.find_element(By.ID, "id_structure_type_specify_value").send_keys('struct type')
        # Submit the form
        self.driver.find_element(By.ID, "btn-submit-vote").click()
        # Proxy to know when sat map is visible 
        # Do this to wait for next page load, else form might not submit properly
        self.wait.until(EC.visibility_of_element_located((By.ID, 'gmimap1')))
