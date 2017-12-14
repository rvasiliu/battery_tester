import unittest
from selenium import webdriver
from fixtures import *


class UserTest(unittest.TestCase):
    def setUp(self):
        # get latest chromdriver from here https://chromedriver.storage.googleapis.com/index.html
        # and copy it to your /bin (sudo)
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_can_login_and_out(self):
        self.browser.get('http://localhost:8000')
        self.assertIn('Glue Login', self.browser.title)

        username = self.browser.find_element_by_id('username')
        password = self.browser.find_element_by_id('password')

        username.send_keys(TEST_USER)
        password.send_keys(TEST_PASS)

        self.browser.find_element_by_id('submit').click()
        self.assertIn('Glue Home', self.browser.title)

        self.browser.find_element_by_id('logout').click()
        self.assertIn('Glue Login', self.browser.title)

if __name__ == '__main__':
    unittest.main()
