import os
import re
import logging
# To debug
import IPython

from selenium.webdriver.common.by import By
from selenium.webdriver import firefox, chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from selenium.webdriver.remote.remote_connection import LOGGER
LOGGER.setLevel(logging.WARNING)

from tests.gui_tests_base import ChromeSeleniumTestsBase, FirefoxSeleniumTestsBase

#TODO: Test Latest activity
#TODO: Test testuser's activity
#TODO: Test modifying a vote and making sure it appears at top, and without duplication

class FirefoxIndexGUITests(FirefoxSeleniumTestsBase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """
    fixtures = ['user.json', 'evalunits.json', 'votes.json', 'survey_v1s.json']


    def test_firefox_user_ranking(self):
        driver = self.driver
        wait = self.wait 

        self._sign_in('/', username='testuser2', password='testpw')
        # Wait until we've redirected to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/"))

        top_users = driver.find_elements(By.XPATH, "//div[@id='leaderboard']/ul[@class='list-group']/li/div/div[@class='vote-user']/strong")
        top_users = [u.text for u in top_users]
        self.assertEquals(top_users[0], 'testuser')
        self.assertEquals(top_users[1], 'testuser2')
        
        # Make user2 submit a vote
        driver.get(f"{self.live_server_url}/survey/v1/id2")

        self._fill_and_submit_form()
        # Return home and verify that user2 now has more votes that 1
        driver.get(f"{self.live_server_url}/")
        top_users = driver.find_elements(By.XPATH, "//div[@id='leaderboard']/ul[@class='list-group']/li/div/div[@class='vote-user']/strong")
        top_users = [u.text for u in top_users]
        self.assertEquals(top_users[0], 'testuser2')
        self.assertEquals(top_users[1], 'testuser')



class ChromeIndexGUITests(ChromeSeleniumTestsBase):
    """
    The live server listens on localhost and binds to port 0 which uses a free port assigned by the OS. 
    The server's URL can be accessed with self.live_server_url during the tests.
    """
    fixtures = ['user.json', 'evalunits.json', 'votes.json', 'survey_v1s.json']


    def test_chrome_user_ranking(self):
        driver = self.driver
        wait = self.wait 

        self._sign_in('/', username='testuser2', password='testpw')
        # Wait until we've redirected to an eval unit
        wait.until(EC.url_contains(f"{self.live_server_url}/"))


        top_users = driver.find_elements(By.XPATH, "//div[@id='leaderboard']/ul[@class='list-group']/li/div/div[@class='vote-user']/strong")
        top_users = [u.text for u in top_users]
        self.assertEquals(top_users[0], 'testuser')
        self.assertEquals(top_users[1], 'testuser2')
        
        # Make user2 submit a vote
        driver.get(f"{self.live_server_url}/survey/v1/id2")

        self._fill_and_submit_form()
        # Return home and verify that user2 now has more votes that 1
        driver.get(f"{self.live_server_url}/")

        top_users = driver.find_elements(By.XPATH, "//div[@id='leaderboard']/ul[@class='list-group']/li/div/div[@class='vote-user']/strong")
        top_users = [u.text for u in top_users]
        self.assertEquals(top_users[0], 'testuser2')
        self.assertEquals(top_users[1], 'testuser')