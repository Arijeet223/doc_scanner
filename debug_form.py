"""
Run this script to see what HTML Microsoft Forms is rendering for questions 1 and 2.
This helps us get the exact XPath selectors needed.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=YqoZ1Uzwqkq9InjY9PVpRY0iK7jNqbdKirfJcvEDPytUNUxNRE5DSlVXVzFINlJTRVFQN0ZGWE9VRC4u"

driver = webdriver.Chrome()
driver.get(FORM_URL)
time.sleep(4)

print("=== ALL RADIO-LIKE OPTIONS (role=radio or role=option) ===")
for el in driver.find_elements(By.XPATH, "//*[@role='radio' or @role='option']"):
    print(repr(el.get_attribute("outerHTML")[:120]))

print("\n=== ALL CLICKABLE DROPDOWN BUTTONS ===")
for el in driver.find_elements(By.XPATH, "//*[@role='combobox' or @role='listbox' or @role='button']"):
    txt = el.text.strip()
    if txt:
        print(repr(el.get_attribute("outerHTML")[:120]))

print("\n=== Click dropdown and see what appears ===")
try:
    dropdown = driver.find_element(By.XPATH, "//*[contains(text(),'Select your answer')]")
    dropdown.click()
    time.sleep(1.5)
    for el in driver.find_elements(By.XPATH, "//*[@role='option' or @role='listitem' or @role='menuitem']"):
        print(repr(el.get_attribute("outerHTML")[:200]))
except Exception as e:
    print(f"Error clicking dropdown: {e}")

print("\nDone. Close this window when done reviewing.")
input()
driver.quit()
