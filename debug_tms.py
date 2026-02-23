"""Quick script to dump the exact HTML of Type of TMS radio options."""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=YqoZ1Uzwqkq9InjY9PVpRY0iK7jNqbdKirfJcvEDPytUNUxNRE5DSlVXVzFINlJTRVFQN0ZGWE9VRC4u"

driver = webdriver.Chrome()
driver.get(FORM_URL)
time.sleep(4)

print("=== ALL VISIBLE TEXT NODES near 'Type of TMS' ===")
try:
    block = driver.find_element(By.XPATH, "//*[contains(text(),'Type of TMS')]/ancestor::*[contains(@class,'question') or @data-automation-id][1]")
    # Find all element children with any text
    children = block.find_elements(By.XPATH, ".//*")
    for c in children:
        t = c.text.strip()
        tag = c.tag_name
        role = c.get_attribute("role") or ""
        if t:
            print(f"  tag={tag}, role={role}, text={repr(t)}, outerHTML={repr(c.get_attribute('outerHTML')[:150])}")
except Exception as e:
    print(f"Error: {e}")

input("\nPress Enter to close...")
driver.quit()
