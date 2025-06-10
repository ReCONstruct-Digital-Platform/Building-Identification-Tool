import os
import re

from selenium.webdriver.common.by import By
from selenium.webdriver import firefox, chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class CommonSeleniumTestsBase(StaticLiveServerTestCase):
    """Common base class for Firefox and Chrome Selenium Tests"""

    def _sign_in(
        self, next_url="/", username="testuser", password="987mysupersecurepassword"
    ):
        self.driver.get(f"{self.live_server_url}/accounts/login/?next={next_url}")
        username_input = self.driver.find_element(By.NAME, "login")
        username_input.send_keys(username)
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        self.driver.find_element(By.ID, "sign-in-button").click()

        # Wait for any redirect to complete
        self.wait.until_not(EC.url_contains("accounts/login"))

        # Print the current URL for debugging
        print(f"After login, redirected to: {self.driver.current_url}")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()


class ChromeSeleniumTestsBase(CommonSeleniumTestsBase):

    @classmethod
    def setUpClass(cls, headless=False):
        super().setUpClass()

        chrome_opts = chrome.options.Options()
        if headless:
            chrome_opts.add_argument("--headless")

        chrome_opts.add_argument("--window-size=1200,900")

        chrome_svc = chrome.service.Service(log_output=os.devnull)
        chrome_driver = chrome.webdriver.WebDriver(
            service=chrome_svc, options=chrome_opts
        )
        chrome_driver.implicitly_wait(10)
        # chrome_driver.maximize_window()  # To avoid layout problems

        cls.driver = chrome_driver
        cls.wait = WebDriverWait(chrome_driver, 10)


class FirefoxSeleniumTestsBase(CommonSeleniumTestsBase):
    @classmethod
    def setUpClass(cls, headless=True):
        super().setUpClass()

        firefox_opts = firefox.options.Options()
        if headless:
            firefox_opts.add_argument("--headless")
        firefox_svc = firefox.service.Service(log_output=os.devnull)
        firefox_driver = firefox.webdriver.WebDriver(
            service=firefox_svc, options=firefox_opts
        )
        firefox_driver.implicitly_wait(10)

        # Hold a driver for each browser
        cls.driver = firefox_driver
        cls.wait = WebDriverWait(firefox_driver, 10)
