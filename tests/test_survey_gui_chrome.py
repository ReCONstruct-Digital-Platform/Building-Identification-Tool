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

from tests.gui_tests_base import ChromeSeleniumTestsBase


class ChromeSurveyGUITests(ChromeSeleniumTestsBase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS.
    The server's URL can be accessed with self.live_server_url during the tests.
    """

    fixtures = ["user.json", "evalunits.json", "emailaddress.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass(headless=True)

    def test_chrome_should_screenshot_satellite_on_survey_tab_click(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")
        # For some reason, the test starts with jobs in the DB already
        # (Presumably from other tests - so delete them here)
        # Assert no pending jobs in DB
        UploadImageJob.objects.all().delete()
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Wait until weève redirected to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id1"))

        # In Selenium we have to wait for the element to appear, otherwise it will
        # click too quickly on the tab, and no screenshot will be taken, since
        # the satellite map will never have been visible. Waiting for the map outer
        # element to be visible is not enough, so we wait on 'gmimap1' as well (red pin)
        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "nav-satellite-tab")))
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

        # Click on an input to trigger uploading
        e = driver.find_element(By.ID, "id_self_similar_cluster_no")
        driver.execute_script("arguments[0].click();", e)
        # Make sure an image upload job was created
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

        time.sleep(1)
        # Switch to the satellite tab and back to survey again
        # NO NEW screenshot should be taken, since the satellite view has not changed
        driver.find_element(By.ID, "nav-satellite-tab").click()

        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))
        driver.find_element(By.ID, "nav-survey-tab").click()
        wait.until(
            EC.visibility_of_element_located((By.ID, "id_self_similar_cluster_specify"))
        )
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

    def test_chrome_modals_should_open_on_info_button_click(self):
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

    def test_chrome_should_screenshot_streetview_on_button_click(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        # In Selenium we have to wait for the element to appear, otherwise it will
        # click too quickly on the tab, and no screenshot will be taken, since
        # the satellite map will never have been visible. Waiting for the map outer
        # element to be visible is not enough, so we wait on 'gmimap1' as well (red pin)
        wait.until(EC.visibility_of_element_located((By.ID, "nav-survey-tab")))
        wait.until(EC.visibility_of_element_located((By.ID, "satellite")))
        # This is a proxy to know when the satellite map is visible
        wait.until(EC.visibility_of_element_located((By.ID, "gmimap1")))

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

    def test_chrome_should_screenshot_streetview_on_spacebar(self):
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
        # There should not be any jobs
        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Now, press the spacebar anywhere on the page
        driver.find_element(By.XPATH, "//body").send_keys(Keys.SPACE)
        wait.until(EC.visibility_of_element_located((By.ID, "screenshot-toast")))
        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 1)

    def test_chrome_should_NOT_screenshot_streetview_on_spacebar_while_inputing(self):
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

        self.assertEqual(UploadImageJob.objects.count(), 0)

        # Scroll down and select a text input, sending the space key to it
        e = driver.find_element(By.ID, "id_site_obstructions_specify_container")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_site_obstructions_specify_value")

        time.sleep(1)
        UploadImageJob.objects.all().delete()
        self.assertEqual(UploadImageJob.objects.count(), 0)

        e.send_keys(Keys.SPACE)

        time.sleep(1)
        self.assertEqual(UploadImageJob.objects.count(), 0)

    def test_survey_chrome_GUI_should_submit_successfully_vanilla(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id1"))
        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        self._fill_and_submit_form()

        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id2"))

        self._fill_and_submit_form()

        # We get redirected back to the first evalunit
        # TODO: Change if we add more eval units to these test cases in the future
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id1"))

    def test_chrome_should_submit_when_clicking_on_labels_or_input_fields(self):
        # As a UX measure, the specify fields should activate when the user clicks on the label
        # or the field itself, behavior supported by custom javascript.

        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id1"))
        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Fill in the form
        # Chrome has a problem where it cant scroll normally like friefox
        e = driver.find_element(By.ID, "id_self_similar_cluster_no")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

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
        driver.execute_script("arguments[0].value = arguments[1];", e, "5")

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
        driver.execute_script("arguments[0].value = arguments[1];", e, "blabla")

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

        # We click on the parent element, which would register the click
        # for both the label and input box. Else Selenium throws an element obscured error
        e = driver.find_element(By.ID, "id_roof_geometry_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_new_or_renovated_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Submit the form
        e = driver.find_element(By.ID, "btn-submit-vote")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Make sure we get redirected to the next eval unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id2"))

    def test_chrome_should_fail_to_submit_when_a_field_is_missing(self):
        driver = self.driver
        wait = self.wait

        self._sign_in("/survey/v1/id1")

        # Test redirect to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/survey/v1/id1"))
        wait.until(EC.presence_of_element_located((By.ID, "nav-survey-tab")))
        driver.find_element(By.ID, "nav-survey-tab").click()

        # Fill in the form
        # Chrome has a problem where it cant scroll normally like friefox
        e = driver.find_element(By.ID, "id_self_similar_cluster_specify")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)
        e = driver.find_element(By.ID, "id_self_similar_cluster_specify_value")
        driver.execute_script("arguments[0].value = arguments[1];", e, "60")

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
        driver.execute_script("arguments[0].value = arguments[1];", e, "5")

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
        driver.execute_script("arguments[0].value = arguments[1];", e, "blabla")

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

        e = driver.find_element(By.ID, "id_roof_geometry_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        e = driver.find_element(By.ID, "id_new_or_renovated_0")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Submit the form
        e = driver.find_element(By.ID, "btn-submit-vote")
        driver.execute_script("arguments[0].scrollIntoView();", e)
        driver.execute_script("arguments[0].click();", e)

        # Check that we did NOT get redirected to the next unit
        wait.until(EC.url_matches(f"{self.live_server_url}/survey/v1/id1"))
