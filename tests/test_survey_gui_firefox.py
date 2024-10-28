import re
import logging
import time

# To debug
import IPython

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER
from buildings.models.models import UploadImageJob
from buildings.models.surveys import SurveyV1Form

LOGGER.setLevel(logging.WARNING)

from tests.gui_tests_base import FirefoxSeleniumTestsBase


class FirefoxSurveyGUITests(FirefoxSeleniumTestsBase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS.
    The server's URL can be accessed with self.live_server_url during the tests.
    """

    fixtures = ["user.json", "evalunits.json", "emailaddress.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass(headless=True)

    def test_firefox_should_screenshot_satellite_on_survey_tab_click(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey")

        # For some reason, the test starts with jobs in the DB already
        # (Presumably from other tests - so delete them here)
        # Assert no pending jobs in DB
        UploadImageJob.objects.all().delete()
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # In Selenium we have to wait for the element to appear, otherwise it will
        # click too quickly on the tab, and no screenshot will be taken, since
        # the satellite map will never have been visible. Waiting for the map outer
        # element to be visible is not enough, so we wait on 'gmimap1' as well (red pin)
        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))
        # This is a proxy to know when the satellite map is visible
        wait.until(EC.visibility_of_element_located((By.ID, "gmimap1")))

        # Click the survey tab
        driver.find_element(By.ID, "nav-survey-tab").click()

        # The satellite screenshot should be stored in the 'data-url' attribute of sat_data
        sat_data = driver.find_element(By.ID, "sat_data")
        wait.until(
            EC.text_to_be_present_in_element_attribute(
                (By.ID, "sat_data"), "data-url", "data:image/png;base64"
            )
        )
        self.assertRegex(sat_data.get_attribute("data-url"), "data:image/png;base64")
        time.sleep(1)

        # However, there should not yet bet an image upload job, since no form field has been filled
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Scroll down and select an input
        e = driver.find_element(By.ID, "id_site_obstructions_specify_container")
        # driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Now there should be an image upload job
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

        # Switch to the satellite tab and back to survey again
        # NO NEW screenshot should be taken, since the satellite view has not changed
        driver.find_element(By.ID, "nav-satellite-tab").click()
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))
        driver.find_element(By.ID, "nav-survey-tab").click()
        wait.until(
            EC.visibility_of_element_located(
                (By.ID, "id_self_similar_cluster_specify_value")
            )
        )
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

    def test_firefox_modals_should_open_on_info_button_click(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        survey = SurveyV1Form()

        fields = list(survey.field_ordering.keys())

        # Not sure why but this is extremely slow, so only try 2 of them
        for field in fields[:2]:
            wait.until(EC.element_to_be_clickable((By.ID, f"{field}_info_btn")))
            driver.find_element(By.ID, f"{field}_info_btn").click()
            wait.until(EC.visibility_of_element_located((By.ID, f"{field}_info")))
            time.sleep(0.25)
            wait.until(EC.visibility_of_element_located((By.ID, f"{field}_info_close")))
            wait.until(EC.element_to_be_clickable((By.ID, f"{field}_info_close")))
            driver.find_element(By.ID, f"{field}_info_close").click()
            wait.until_not(
                (EC.visibility_of_element_located((By.CLASS_NAME, "modal-backdrop")))
            )

    def test_firefox_should_screenshot_streetview_on_button_click(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        # In Selenium we have to wait for the element to appear, otherwise it will
        # click too quickly on the tab, and no screenshot will be taken, since
        # the satellite map will never have been visible. Waiting for the map outer
        # element to be visible is not enough, so we wait on 'gmimap1' as well (red pin)
        wait.until(EC.visibility_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))

        # For some reason, the test starts with jobs in the DB already
        # (Presumably from other tests - so delete them here)
        # Assert no pending jobs in DB
        UploadImageJob.objects.all().delete()
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Click on the screenshot button, it should pop up a toast
        # and insert a new job for the Streetview image in the DB
        driver.find_element(By.ID, "btn-screenshot").click()

        wait.until(EC.visibility_of_element_located((By.ID, "screenshot-toast")))
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

    def test_firefox_should_screenshot_streetview_on_spacebar(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        # In Selenium we have to wait for the element to appear, otherwise it will
        # click too quickly on the tab, and no screenshot will be taken, since
        # the satellite map will never have been visible. Waiting for the map outer
        # element to be visible is not enough, so we wait on 'gmimap1' as well (red pin)
        wait.until(EC.visibility_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))

        # Click the survey tab
        driver.find_element(By.ID, "nav-survey-tab").click()
        time.sleep(1)

        # Has normally screenshotted satellite, so delete all jobs
        UploadImageJob.objects.all().delete()
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Now, press the spacebar while entering text in an input
        # it should do the same as above
        driver.find_element(By.XPATH, "//body").send_keys(Keys.SPACE)
        wait.until(EC.visibility_of_element_located((By.ID, "screenshot-toast")))
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

    def test_firefox_should_NOT_screenshot_streetview_on_spacebar_while_inputing(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        # In Selenium we have to wait for the element to appear, otherwise it will
        # click too quickly on the tab, and no screenshot will be taken, since
        # the satellite map will never have been visible. Waiting for the map outer
        # element to be visible is not enough, so we wait on 'gmimap1' as well (red pin)
        wait.until(EC.visibility_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))

        # Delte any previous jobs
        UploadImageJob.objects.all().delete()
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Click the survey tab
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Scroll down and select a text input, sending the space key to it
        e = driver.find_element(By.ID, "id_site_obstructions_specify_container")
        # driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_site_obstructions_specify_value")
        e.send_keys(Keys.SPACE)

        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

    def test_firefox_should_submit_successfully_vanilla(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Fill in and submit the form
        self._fill_and_submit_form()

        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id2"))

        # Fill in and submit the form
        self._fill_and_submit_form()

        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id1"))

    def test_firefox_should_submit_successfully_when_clicking_on_labels_or_input_fields(
        self,
    ):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id1"))
        wait.until(EC.visibility_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))

        driver.find_element(By.ID, "nav-survey-tab").click()

        # Fill in the form
        wait.until(
            EC.presence_of_element_located(
                (By.ID, "id_self_similar_cluster_specify_value")
            )
        )
        wait.until(
            EC.visibility_of_element_located(
                (By.ID, "id_self_similar_cluster_specify_value")
            )
        )
        driver.find_element(By.ID, "id_self_similar_cluster_specify_container").click()
        driver.find_element(By.ID, "id_self_similar_cluster_specify_value").send_keys(
            "15"
        )

        wait.until(EC.presence_of_element_located((By.ID, "id_has_simple_footprint_0")))
        wait.until(
            EC.visibility_of_element_located((By.ID, "id_has_simple_footprint_0"))
        )
        driver.find_element(By.ID, "id_has_simple_footprint_0").click()

        wait.until(EC.presence_of_element_located((By.ID, "id_has_simple_volume_1")))
        wait.until(EC.visibility_of_element_located((By.ID, "id_has_simple_volume_1")))
        driver.find_element(By.ID, "id_has_simple_volume_1").click()
        # Click on the box to enter value directly (need to actually click on the parent element)
        # else selenium throws an error about the element being obscured
        driver.find_element(By.ID, "id_num_storeys_specify_container").click()
        driver.find_element(By.ID, "id_num_storeys_specify_value").send_keys("5")
        driver.find_element(By.ID, "id_has_basement_2").click()
        driver.find_element(By.ID, "id_site_obstructions_0").click()
        # Click on the parent element
        driver.find_element(By.ID, "id_appendages_specify_container").click()
        driver.find_element(By.ID, "id_appendages_specify_value").send_keys("blabla")

        # Here we test clicking on the label of a non-specify field, it should work as well
        checkbox = driver.find_element(By.ID, "id_appendages_0")
        checkbox.find_element(By.XPATH, "..").click()

        driver.find_element(By.ID, "id_exterior_cladding_5").click()
        driver.find_element(By.ID, "id_facade_condition_0").click()
        driver.find_element(By.ID, "id_window_wall_ratio_2").click()
        driver.find_element(By.ID, "id_large_irregular_windows_0").click()
        driver.find_element(By.ID, "id_roof_geometry_3").click()
        driver.find_element(By.ID, "id_new_or_renovated_0").click()

        # Submit the form
        driver.find_element(By.ID, "btn-submit-vote").click()
        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id2"))

    def test_firefox_should_remove_values_when_unselecting_specify_fields(self):
        """
        Test that when a user unselects one of the radio specifies
        their previously entered values are deleted and the field is disactivated
        """
        driver = self.driver
        wait = self.wait

        # Login and go on the survey
        self._sign_in("/survey/v1/id1")

        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Test the NumberOrUnsure field
        specify_radio_elem = driver.find_element(By.ID, "id_num_storeys_specify")
        specify_radio_elem.click()
        number_input_elem = driver.find_element(By.ID, "id_num_storeys_specify_value")
        number_input_elem.send_keys("5")
        self.assertEqual(number_input_elem.get_attribute("value"), "5")
        # Click on another radio, thus unselecting the specify
        driver.find_element(By.ID, "id_num_storeys_unsure").click()
        # Make sure the number input is disabled and has no value
        wait.until(
            EC.element_attribute_to_include(
                (By.ID, "id_num_storeys_specify_value"), "disabled"
            )
        )
        self.assertEqual(number_input_elem.get_attribute("value"), "")
        # check that the radio is not checked (returns None instead of false)
        self.assertEqual(specify_radio_elem.get_attribute("checked"), None)

        # Test a RadioWithSpecify field
        specify_radio_elem = driver.find_element(
            By.ID, "id_self_similar_cluster_specify"
        )
        specify_radio_elem.click()
        specify_text_input_elem = driver.find_element(
            By.ID, "id_self_similar_cluster_specify_value"
        )
        specify_text_input_elem.send_keys("5")
        self.assertEqual(specify_text_input_elem.get_attribute("value"), "5")

        # Clicking the SAME radio field, should do NOTHING
        specify_radio_elem.click()
        self.assertEqual(specify_text_input_elem.get_attribute("value"), "5")

        # Click on another radio
        driver.find_element(By.ID, "id_self_similar_cluster_no").click()
        # Make sure the number input is disabled and has no value
        wait.until(
            EC.element_attribute_to_include(
                (By.ID, "id_self_similar_cluster_specify_value"), "disabled"
            )
        )
        self.assertEqual(specify_text_input_elem.get_attribute("value"), "")
        # check that the radio is not checked (returns None instead of false)
        self.assertEqual(specify_radio_elem.get_attribute("checked"), None)

        # Test a multiple checkbox
        specify_checkbox = driver.find_element(By.ID, "id_appendages_specify")
        specify_checkbox.click()
        specify_input_field = driver.find_element(By.ID, "id_appendages_specify_value")
        specify_input_field.send_keys("blabla")
        self.assertEqual(specify_input_field.get_attribute("value"), "blabla")
        # Click on another checkbox
        # This should NOT delete the value, as we can select multiple
        driver.find_element(By.ID, "id_appendages_0").click()
        # Checkbox should still be checked, the input field should be enabled and have its value!
        self.assertEqual(specify_checkbox.get_attribute("checked"), "true")
        self.assertEqual(specify_input_field.get_attribute("disabled"), None)
        self.assertEqual(specify_input_field.get_attribute("value"), "blabla")
        # Now clicking it again however should unselect it
        specify_checkbox.click()
        self.assertEqual(specify_input_field.get_attribute("value"), "")
        self.assertEqual(specify_checkbox.get_attribute("checked"), None)
        self.assertEqual(specify_input_field.get_attribute("disabled"), "true")

        # Try the unselecting again, this time clicking the parent element
        specify_checkbox.click()
        specify_input_field.send_keys("blabla")
        self.assertEqual(specify_input_field.get_attribute("value"), "blabla")

        # Now click the label, and it should unselect it
        # Clicking the parent id_appendages_specify_container does not work here, (for a reason I don't understand)
        # But clicking on the LABEL works
        driver.find_element(
            By.XPATH, "//div[@id='id_appendages_specify_container']//label"
        ).click()
        self.assertEqual(specify_checkbox.get_attribute("checked"), None)
        self.assertEqual(specify_input_field.get_attribute("value"), "")
        self.assertEqual(specify_input_field.get_attribute("disabled"), "true")

    def test_firefox_should_fail_to_submit_when_input_is_missing(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")
        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id1"))

        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Fill in the form
        wait.until(
            EC.visibility_of_element_located((By.ID, "id_self_similar_cluster_specify"))
        )
        driver.find_element(By.ID, "id_self_similar_cluster_specify").click()
        driver.find_element(By.ID, "id_self_similar_cluster_specify_value").send_keys(
            "6"
        )

        wait.until(EC.presence_of_element_located((By.ID, "id_has_simple_footprint_0")))
        wait.until(
            EC.visibility_of_element_located((By.ID, "id_has_simple_footprint_0"))
        )
        driver.find_element(By.ID, "id_has_simple_footprint_0").click()

        wait.until(EC.presence_of_element_located((By.ID, "id_has_simple_volume_1")))
        wait.until(EC.visibility_of_element_located((By.ID, "id_has_simple_volume_1")))
        driver.find_element(By.ID, "id_has_simple_volume_1").click()
        # num storeys value is MISSING
        driver.find_element(By.ID, "id_num_storeys_specify").click()

        driver.find_element(By.ID, "id_has_basement_2").click()
        driver.find_element(By.ID, "id_site_obstructions_0").click()

        driver.find_element(By.ID, "id_appendages_specify").click()
        driver.find_element(By.ID, "id_appendages_specify_value").send_keys("blabla")

        driver.find_element(By.ID, "id_exterior_cladding_5").click()
        driver.find_element(By.ID, "id_facade_condition_0").click()
        driver.find_element(By.ID, "id_window_wall_ratio_2").click()
        driver.find_element(By.ID, "id_large_irregular_windows_0").click()
        driver.find_element(By.ID, "id_roof_geometry_3").click()
        driver.find_element(By.ID, "id_new_or_renovated_0").click()

        # Submit the form - should not work
        driver.find_element(By.ID, "btn-submit-vote").click()
        # Make sure we stayed at the same URL indicating failure to submit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id1"))
