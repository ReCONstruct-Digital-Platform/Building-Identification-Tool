import os
import re
import logging
# To debug
import IPython

from selenium.webdriver.common.by import By
from selenium.webdriver import firefox, chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.webdriver.remote.remote_connection import LOGGER
LOGGER.setLevel(logging.WARNING)


class SeleniumFirefoxTests(StaticLiveServerTestCase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """
    fixtures = ['user.json', 'evalunits.json']

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

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()


    def test_survey_GUI_firefox_should_submit_successfully_vanilla(self):

        driver = self.driver
        wait = self.wait 

        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

        driver.get(f"{self.live_server_url}/survey/v1/id1")
        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        wait.until(EC.presence_of_element_located((By.ID, 'sat_data')))
        # Check the satellite screenshot was taken
        sat_data = driver.find_element(By.ID, "sat_data")
        wait.until(EC.text_to_be_present_in_element_attribute((By.ID, 'sat_data'), 'data-url', 'data:image/png;base64'))
        self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64')

        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
        eval_unit_id = m.group(1)

        if eval_unit_id == '1':
            next_eval_unit_id = '2'
        else:
            next_eval_unit_id = '1'

        # Fill in the form
        wait.until(EC.presence_of_element_located((By.ID, 'id_has_simple_footprint_0')))
        wait.until(EC.visibility_of_element_located((By.ID, 'id_has_simple_footprint_0')))
        driver.find_element(By.ID, "id_has_simple_footprint_0").click()
        wait.until(EC.presence_of_element_located((By.ID, 'id_has_simple_volume_1')))
        wait.until(EC.visibility_of_element_located((By.ID, 'id_has_simple_volume_1')))
        driver.find_element(By.ID, "id_has_simple_volume_1").click()
        driver.find_element(By.ID, "id_num_storeys_specify").click()
        driver.find_element(By.ID, "id_num_storeys_specify_value").send_keys('5')
        driver.find_element(By.ID, "id_num_storeys_unsure").click()
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
        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{next_eval_unit_id}"))


    def test_survey_GUI_firefox_should_submit_successfully_when_clicking_on_labels_or_input_fields(self):
        driver = self.driver
        wait = self.wait 

        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

        driver.get(f"{self.live_server_url}/survey/v1/id1")
        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        wait.until(EC.presence_of_element_located((By.ID, 'sat_data')))
        # Check the satellite screenshot was taken
        sat_data = driver.find_element(By.ID, "sat_data")
        wait.until(EC.text_to_be_present_in_element_attribute((By.ID, 'sat_data'), 'data-url', 'data:image/png;base64'))
        self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64')

        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
        eval_unit_id = m.group(1)
        if eval_unit_id == '1':
            next_eval_unit_id = '2'
        else:
            next_eval_unit_id = '1'

        # Fill in the form
        wait.until(EC.presence_of_element_located((By.ID, 'id_has_simple_footprint_0')))
        wait.until(EC.visibility_of_element_located((By.ID, 'id_has_simple_footprint_0')))
        driver.find_element(By.ID, "id_has_simple_footprint_0").click()
        wait.until(EC.presence_of_element_located((By.ID, 'id_has_simple_volume_1')))
        wait.until(EC.visibility_of_element_located((By.ID, 'id_has_simple_volume_1')))
        driver.find_element(By.ID, "id_has_simple_volume_1").click()
        # Click on the box to enter value directly (need to actually click on the parent element)
        # else selenium throws an error about the element being obscured
        driver.find_element(By.ID, "id_num_storeys_specify_container").click()
        driver.find_element(By.ID, "id_num_storeys_specify_value").send_keys('5')
        driver.find_element(By.ID, "id_has_basement_2").click()
        driver.find_element(By.ID, "id_site_obstructions_0").click()
        # Click on the parent element
        driver.find_element(By.ID, "id_appendages_specify_container").click()
        driver.find_element(By.ID, "id_appendages_specify_value").send_keys('blabla')
        # Here we test clicking on the label of a non-specify field, it should work as well
        checkbox = driver.find_element(By.ID, "id_appendages_0")
        checkbox.find_element(By.XPATH, '..').click()

        driver.find_element(By.ID, "id_exterior_cladding_5").click()
        driver.find_element(By.ID, "id_facade_condition_0").click()
        driver.find_element(By.ID, "id_window_wall_ratio_2").click()
        driver.find_element(By.ID, "id_large_irregular_windows_0").click()
        driver.find_element(By.ID, "id_roof_geometry_3").click()
        # Click on the parent element
        driver.find_element(By.ID, "id_structure_type_specify_container").click()
        driver.find_element(By.ID, "id_structure_type_specify_value").send_keys('struct type')

        # Submit the form - will FAIL
        driver.find_element(By.ID, "btn-submit-vote").click()
        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{next_eval_unit_id}"))


    def test_survey_GUI_firefox_should_remove_values_when_unselecting_specify_fields(self):
        # Test that when a user unselects one of the radio specifies
        # their previously entered values are deleted and the field is disactivated 
        driver = self.driver
        wait = self.wait 

        # Login and go on the survey
        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        driver.get(f"{self.live_server_url}/survey/v1/id1")
        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Test the NumberOrUnsure field
        specify_radio_elem = driver.find_element(By.ID, "id_num_storeys_specify")
        specify_radio_elem.click()
        number_input_elem = driver.find_element(By.ID, "id_num_storeys_specify_value")
        number_input_elem.send_keys('5')
        self.assertEqual(number_input_elem.get_attribute('value'), '5')
        # Click on another radio, thus unselecting the specify
        driver.find_element(By.ID, "id_num_storeys_unsure").click()
        # Make sure the number input is disabled and has no value
        wait.until(EC.element_attribute_to_include((By.ID, "id_num_storeys_specify_value"), 'disabled'))
        self.assertEqual(number_input_elem.get_attribute('value'), '')
        # check that the radio is not checked (returns None instead of false)
        self.assertEqual(specify_radio_elem.get_attribute('checked'), None)

        # Test a RadioWithSpecify field
        specify_radio_elem = driver.find_element(By.ID, "id_structure_type_specify")
        specify_radio_elem.click()
        specify_text_input_elem = driver.find_element(By.ID, "id_structure_type_specify_value")
        specify_text_input_elem.send_keys('struct type')
        self.assertEqual(specify_text_input_elem.get_attribute('value'), 'struct type')
        # Clicking the SAME radio field, should do NOTHING
        specify_radio_elem.click()
        self.assertEqual(specify_text_input_elem.get_attribute('value'), 'struct type')

        # Click on another radio
        driver.find_element(By.ID, "id_structure_type_0").click()   
        # Make sure the number input is disabled and has no value
        wait.until(EC.element_attribute_to_include((By.ID, "id_structure_type_specify_value"), 'disabled'))
        self.assertEqual(specify_text_input_elem.get_attribute('value'), '')
        # check that the radio is not checked (returns None instead of false)
        self.assertEqual(specify_radio_elem.get_attribute('checked'), None)

        # Test a multiple checkbox
        specify_checkbox = driver.find_element(By.ID, "id_appendages_specify")
        specify_checkbox.click()
        specify_input_field = driver.find_element(By.ID, "id_appendages_specify_value")
        specify_input_field.send_keys('blabla')
        self.assertEqual(specify_input_field.get_attribute('value'), 'blabla')
        # Click on another checkbox
        # This should NOT delete the value, as we can select multiple
        driver.find_element(By.ID, "id_appendages_0").click()
        # Checkbox should still be checked, the input field should be enabled and have its value!
        self.assertEqual(specify_checkbox.get_attribute('checked'), 'true')
        self.assertEqual(specify_input_field.get_attribute('disabled'), None)
        self.assertEqual(specify_input_field.get_attribute('value'), 'blabla')
        # Now clicking it again however should unselect it
        specify_checkbox.click()
        self.assertEqual(specify_input_field.get_attribute('value'), '')
        self.assertEqual(specify_checkbox.get_attribute('checked'), None)
        self.assertEqual(specify_input_field.get_attribute('disabled'), 'true')

        # Try the unselecting again, this time clicking the parent element
        specify_checkbox.click()
        specify_input_field.send_keys('blabla')
        self.assertEqual(specify_input_field.get_attribute('value'), 'blabla')

        # Now click the label, and it should unselect it
        # Clicking the parent id_appendages_specify_container does not work here, (for a reason I don't understand)
        # But clicking on the LABEL works
        driver.find_element(By.XPATH, "//div[@id='id_appendages_specify_container']//label").click()
        self.assertEqual(specify_checkbox.get_attribute('checked'), None)
        self.assertEqual(specify_input_field.get_attribute('value'), '')
        self.assertEqual(specify_input_field.get_attribute('disabled'), 'true')


    def test_survey_GUI_firefox_should_fail_to_submit_when_input_is_missing(self):
        driver = self.driver
        wait = self.wait 

        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

        driver.get(f"{self.live_server_url}/survey/v1/id1")
        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        wait.until(EC.presence_of_element_located((By.ID, 'sat_data')))
        # Check the satellite screenshot was taken
        sat_data = driver.find_element(By.ID, "sat_data")
        wait.until(EC.text_to_be_present_in_element_attribute((By.ID, 'sat_data'), 'data-url', 'data:image/png;base64'))
        self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64')

        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
        eval_unit_id = m.group(1)

        # Fill in the form
        wait.until(EC.presence_of_element_located((By.ID, 'id_has_simple_footprint_0')))
        wait.until(EC.visibility_of_element_located((By.ID, 'id_has_simple_footprint_0')))
        driver.find_element(By.ID, "id_has_simple_footprint_0").click()
        wait.until(EC.presence_of_element_located((By.ID, 'id_has_simple_volume_1')))
        wait.until(EC.visibility_of_element_located((By.ID, 'id_has_simple_volume_1')))
        driver.find_element(By.ID, "id_has_simple_volume_1").click()
        # num storeys value is MISSING
        driver.find_element(By.ID, "id_num_storeys_specify").click()

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

        # Submit the form - should not work
        driver.find_element(By.ID, "btn-submit-vote").click()
        # Make sure we stayed at the same URL indicating failure to submit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{eval_unit_id}"))



class SeleniumChromeTests(StaticLiveServerTestCase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """
    LOGGER.setLevel(logging.ERROR)
    fixtures = ['user.json', 'evalunits.json']

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


    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()


    def test_submit_survey_chrome_clicking_on_inputs(self):
        driver = self.driver
        wait = self.wait 

        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()


        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

        driver.get(f"{self.live_server_url}/survey/v1/id1")

        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        wait.until(EC.presence_of_element_located((By.ID, 'sat_data')))
        wait.until(EC.text_to_be_present_in_element_attribute((By.ID, 'sat_data'), 'data-url', 'data:image/png;base64,'))
        # Check the satellite screenshot was taken
        sat_data = driver.find_element(By.ID, "sat_data")
        self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64,')

        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
        eval_unit_id = m.group(1)

        if eval_unit_id == '1':
            next_eval_unit_id = '2'
        else:
            next_eval_unit_id = '1'

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

        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{next_eval_unit_id}"))


    def test_survey_GUI_chrome_should_submit_when_clicking_on_labels_or_input_fields(self):
        # As a UX measure, the specify fields should activate when the user clicks on the label
        # or the field itself, behavior supported by custom javascript.

        driver = self.driver
        wait = self.wait 

        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()


        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

        driver.get(f"{self.live_server_url}/survey/v1/id1")

        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        wait.until(EC.presence_of_element_located((By.ID, 'sat_data')))
        wait.until(EC.text_to_be_present_in_element_attribute((By.ID, 'sat_data'), 'data-url', 'data:image/png;base64,'))
        # Check the satellite screenshot was taken
        sat_data = driver.find_element(By.ID, "sat_data")
        self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64,')

        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
        eval_unit_id = m.group(1)

        if eval_unit_id == '1':
            next_eval_unit_id = '2'
        else:
            next_eval_unit_id = '1'

        # Fill in the form
        # Chrome has a problem where it cant scroll normally like friefox
        e = driver.find_element(By.ID, "id_has_simple_footprint_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_has_simple_volume_1")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # We click on the parent element, which would register the click
        # for both the label and input box. Else Selenium throws an element obscured error
        e = driver.find_element(By.ID, "id_num_storeys_specify_container")
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

        # We click on the parent element, which would register the click
        # for both the label and input box. Else Selenium throws an element obscured error
        e = driver.find_element(By.ID, "id_appendages_specify_container")
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

        # We click on the parent element, which would register the click
        # for both the label and input box. Else Selenium throws an element obscured error
        e = driver.find_element(By.ID, "id_structure_type_specify_container")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_structure_type_specify_value")
        driver.execute_script("arguments[0].value = arguments[1];", e, 'struct type')

        # Submit the form
        e = driver.find_element(By.ID, "btn-submit-vote")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{next_eval_unit_id}"))


    def test_survey_GUI_chrome_should_remove_values_when_unselecting_specify_fields(self):
        # Test that when a user unselects one of the radio specifies
        # their previously entered values are deleted and the field is disactivated 
        driver = self.driver
        wait = self.wait 

        # Login and go on the survey
        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        driver.get(f"{self.live_server_url}/survey/v1/id1")
        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Test the NumberOrUnsure field
        specify_radio_elem = driver.find_element(By.ID, "id_num_storeys_specify")
        driver.execute_script("arguments[0].scrollIntoView();", specify_radio_elem)
        # driver.execute_script("arguments[0].click();", specify_radio_elem)
        specify_radio_elem.click()
        number_input_elem = driver.find_element(By.ID, "id_num_storeys_specify_value")
        driver.execute_script("arguments[0].scrollIntoView();", number_input_elem)
        number_input_elem.send_keys('5')

        self.assertEqual(number_input_elem.get_attribute('value'), '5')
        # Click on another radio, thus unselecting the specify
        driver.find_element(By.ID, "id_num_storeys_unsure").click()
        # Make sure the number input is disabled and has no value
        wait.until(EC.element_attribute_to_include((By.ID, "id_num_storeys_specify_value"), 'disabled'))
        self.assertEqual(number_input_elem.get_attribute('value'), '')
        # check that the radio is not checked (returns None instead of false)
        self.assertEqual(specify_radio_elem.get_attribute('checked'), None)

        # Test a RadioWithSpecify field
        specify_radio_elem = driver.find_element(By.ID, "id_structure_type_specify")
        specify_radio_elem.click()
        specify_text_input_elem = driver.find_element(By.ID, "id_structure_type_specify_value")
        specify_text_input_elem.send_keys('struct type')
        self.assertEqual(specify_text_input_elem.get_attribute('value'), 'struct type')
        # Clicking the same radio should not unselect it
        specify_radio_elem.click()
        self.assertEqual(specify_text_input_elem.get_attribute('value'), 'struct type')

        # Clicking on another radio should unselect it and delte the entered value
        driver.find_element(By.ID, "id_structure_type_0").click()   
        # Make sure the number input is disabled and has no value
        wait.until(EC.element_attribute_to_include((By.ID, "id_structure_type_specify_value"), 'disabled'))
        self.assertEqual(specify_text_input_elem.get_attribute('value'), '')
        # check that the radio is not checked (returns None instead of false)
        self.assertEqual(specify_radio_elem.get_attribute('checked'), None)

        # Test a multiple checkbox
        specify_checkbox = driver.find_element(By.ID, "id_appendages_specify")
        specify_checkbox.click()
        specify_input_field = driver.find_element(By.ID, "id_appendages_specify_value")
        specify_input_field.send_keys('blabla')
        self.assertEqual(specify_input_field.get_attribute('value'), 'blabla')
        # Click on another checkbox
        # This should NOT delete the value, as we can select multiple
        driver.find_element(By.ID, "id_appendages_0").click()
        # Checkbox should stil lbe checked, not disabled, and have its value!
        self.assertEqual(specify_input_field.get_attribute('value'), 'blabla')
        self.assertEqual(specify_checkbox.get_attribute('checked'), 'true')
        self.assertEqual(specify_input_field.get_attribute('disabled'), None)
        # Now clicking it again however should unselect it
        specify_checkbox.click()
        self.assertEqual(specify_input_field.get_attribute('value'), '')
        self.assertEqual(specify_checkbox.get_attribute('checked'), None)
        self.assertEqual(specify_input_field.get_attribute('disabled'), 'true')

        # Try the unselecting again, this time clicking the parent element
        specify_checkbox.click()
        specify_input_field.send_keys('blabla')
        self.assertEqual(specify_input_field.get_attribute('value'), 'blabla')

        # Now click the label, and it should unselect it
        # Clicking the parent id_appendages_specify_container does not work here, (for a reason I don't understand)
        # But clicking on the LABEL works
        driver.find_element(By.XPATH, "//div[@id='id_appendages_specify_container']//label").click()
        self.assertEqual(specify_input_field.get_attribute('value'), '')
        self.assertEqual(specify_checkbox.get_attribute('checked'), None)
        self.assertEqual(specify_input_field.get_attribute('disabled'), 'true')


    def testt_survey_GUI_chrome_should_fail_to_submit_when_a_field_is_missing(self):
        driver = self.driver
        wait = self.wait 

        driver.get(f"{self.live_server_url}/login?next=/survey")
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("testpw")
        driver.find_element(By.XPATH, '//input[@value="Login"]').click()
        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id"))

        driver.get(f"{self.live_server_url}/survey/v1/id1")

        wait.until(EC.presence_of_element_located((By.ID, 'nav-survey-tab')))
        wait.until(EC.visibility_of_element_located((By.ID, 'satmap')))
        driver.find_element(By.ID, "nav-survey-tab").click()

        wait.until(EC.presence_of_element_located((By.ID, 'sat_data')))
        wait.until(EC.text_to_be_present_in_element_attribute((By.ID, 'sat_data'), 'data-url', 'data:image/png;base64,'))
        # Check the satellite screenshot was taken
        sat_data = driver.find_element(By.ID, "sat_data")
        self.assertRegex(sat_data.get_attribute('data-url'), 'data:image/png;base64,')

        m = re.match(rf'{self.live_server_url}/survey/v1/id([0-9])', driver.current_url)
        eval_unit_id = m.group(1)

        # Fill in the form
        # Chrome has a problem where it cant scroll normally like friefox
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
        # Clicking it again will undo the previous work and make the form invalid!
        e = driver.find_element(By.ID, "id_appendages_specify")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

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

        # Check that we did NOT get redirected to the next unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id{eval_unit_id}"))
