from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def fill_form(form_url, data):
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)

    wait = WebDriverWait(driver, 15)

    try:
        driver.get(form_url)
        # Wait for form to fully load
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Name of Processor')]")))
        time.sleep(2)

        print(f"Filling out form for case: {data['case_number']}...")

        # ─── HELPER: click a radio / span option by its visible label ───────────
        def click_option(label_text):
            clicked = False
            strategies = [
                # Exact text on any element (most common MS Forms radio)
                f"//*[normalize-space(text())='{label_text}']",
                # Contains text (handles invisible chars or nested formatting)
                f"//*[contains(normalize-space(text()),'{label_text}')]",
                # Label for a radio input that contains the text
                f"//label[contains(normalize-space(.), '{label_text}')]",
                # Aria-label attribute match
                f"//*[@aria-label='{label_text}' or contains(@aria-label,'{label_text}')]",
            ]
            for xpath in strategies:
                try:
                    el = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    el.click()
                    time.sleep(0.5)
                    print(f"  ✔ Clicked option: {label_text}")
                    clicked = True
                    break
                except:
                    continue
            if not clicked:
                print(f"  ✘ Could not click option '{label_text}' with any strategy")

        # ─── HELPER: open a dropdown by clicking "Select your answer" near a title, then pick option ────
        def select_dropdown(question_title, option_text):
            try:
                # Click the dropdown button — look for the button/div containing "Select your answer"
                # that is inside the question block with the given title
                dropdown_xpath = (
                    f"//*[normalize-space(text())='{question_title}']"
                    f"/ancestor::*[@data-automation-id or contains(@class,'question')]"
                    f"//*[contains(@class,'select') or @role='combobox' or @role='button' or contains(@class,'dropdown-placeholder')]"
                )
                try:
                    btn = driver.find_element(By.XPATH, dropdown_xpath)
                except:
                    # broader fallback: just find the "Select your answer" button
                    btn = driver.find_element(By.XPATH, "//*[contains(text(),'Select your answer')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                btn.click()
                time.sleep(1.5)

                # After clicking, the list items appear. MS Forms uses divs with aria-selected
                option_el = wait.until(EC.element_to_be_clickable(
                    (By.XPATH,
                     f"//*[@aria-selected][normalize-space(.)='{option_text}'] | "
                     f"//*[@role='option'][normalize-space(.)='{option_text}'] | "
                     f"//*[normalize-space(text())='{option_text}' and ancestor::*[@role='listbox' or @role='menu']]")))
                driver.execute_script("arguments[0].scrollIntoView(true);", option_el)
                option_el.click()
                time.sleep(0.5)
                print(f"  ✔ Dropdown selected: {option_text}")
            except Exception as e:
                print(f"  ✘ Dropdown failed for '{question_title}'/'{option_text}': {e}")

        # ─── HELPER: fill a text box by the question title ──────────────────────
        def fill_text(question_title, value):
            if not value:
                return
            try:
                input_el = driver.find_element(By.XPATH,
                    f"//*[normalize-space(text())='{question_title}']"
                    f"/ancestor::*[@data-automation-id or contains(@class,'question')]"
                    f"//input[not(@type='radio') and not(@type='checkbox') and not(@type='hidden')] | "
                    f"//*[normalize-space(text())='{question_title}']"
                    f"/ancestor::*[@data-automation-id or contains(@class,'question')]//textarea"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", input_el)
                input_el.click()
                # Clear then type
                input_el.send_keys(Keys.CONTROL + "a")
                input_el.send_keys(Keys.DELETE)
                input_el.send_keys(value)
                time.sleep(0.3)
                print(f"  ✔ Filled '{question_title}': {value}")
            except Exception as e:
                print(f"  ✘ Could not fill '{question_title}': {e}")


        # ════════════════════════════════════════════════════════
        # FILL EACH FIELD
        # ════════════════════════════════════════════════════════

        # 1. Name of Processor — DROPDOWN
        select_dropdown("Name of Processor", data["processor_name"])

        # 2. Type of TMS — always 2.O (capital letter O, not zero)
        click_option("2.O")

        # 3. Claim Sub Type — always CASHLESS
        click_option("Cashless")

        # 4. Scheme — RADIO
        click_option(data["scheme"])

        # 5. Claim Type — RADIO
        click_option(data["claim_type"])

        # 6. Role — RADIO
        click_option(data["role"])

        # 7. Case Number — TEXT
        fill_text("Case Number", data["case_number"])

        # 8. Claimed Amount — NUMBER
        fill_text("Claimed Amount", data["claimed_amount"])

        # 9. Approved Amount — NUMBER
        fill_text("Approved Amount", data["approved_amount"])

        # 10. No of Pages — NUMBER (always empty per user logic)
        # fill_text("No of Pages", data["no_of_pages"])

        # 11. Case Type — RADIO
        click_option(data["case_type"])

        # 12. Deficiencies Noticed by CEX — always "Other" + fill its text box
        click_option("Other")
        time.sleep(1.2)
        deficiencies_value = data.get("deficiencies_text", "NA")
        other_filled = False
        # Strategy 1: look for input/textarea inside the Deficiencies question block
        other_input_strategies = [
            # Input near the "Other" label inside the Deficiencies question block
            "//*[contains(normalize-space(text()),'Deficiencies Noticed')]"
            "/ancestor::*[@data-automation-id or contains(@class,'question')]"
            "//input[@type='text' and not(@type='hidden')] | "
            "//*[contains(normalize-space(text()),'Deficiencies Noticed')]"
            "/ancestor::*[@data-automation-id or contains(@class,'question')]//textarea",
            # Generic: any input labelled/near 'Other'
            "//input[@aria-label='Other' or contains(@placeholder,'Other') or contains(@placeholder,'specify')]",
            # Generic: textarea labelled/near 'Other'
            "//textarea[@aria-label='Other' or contains(@placeholder,'Other') or contains(@placeholder,'specify')]",
            # Last-resort: last visible text input on the page
            "(//input[@type='text' and not(@type='hidden')])[last()]",
        ]
        for xpath in other_input_strategies:
            try:
                other_input = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].scrollIntoView(true);", other_input)
                other_input.click()
                other_input.send_keys(Keys.CONTROL + "a")
                other_input.send_keys(Keys.DELETE)
                other_input.send_keys(deficiencies_value)
                time.sleep(0.4)
                print(f"  ✔ Filled Other deficiency text: {deficiencies_value}")
                other_filled = True
                break
            except:
                continue
        if not other_filled:
            print(f"  ✘ Could not fill Other deficiency text (tried all strategies)")

        # 13. Action Taken — RADIO (Approved / Approved With Deduction / Query / Reject)
        click_option(data["action_taken"])

        # 14. Reasons — TEXTAREA (question title is long, use contains match)
        try:
            reasons_el = driver.find_element(By.XPATH,
                "//*[contains(normalize-space(text()),'Reasons for Query')]"
                "/ancestor::*[@data-automation-id or contains(@class,'question')]"
                "//input[not(@type='radio') and not(@type='checkbox') and not(@type='hidden')] | "
                "//*[contains(normalize-space(text()),'Reasons for Query')]"
                "/ancestor::*[@data-automation-id or contains(@class,'question')]//textarea"
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", reasons_el)
            reasons_el.click()
            reasons_el.send_keys(Keys.CONTROL + "a")
            reasons_el.send_keys(Keys.DELETE)
            reasons_el.send_keys(data["reason"])
            time.sleep(0.3)
            print(f"  ✔ Filled Reasons: {data['reason']}")
        except Exception as e:
            print(f"  ✘ Could not fill Reasons: {e}")

        # 15. Other Remarks — always NA
        fill_text("Other Remarks", "NA")

        time.sleep(1)
        print("\n✔ Form fully filled! Please review in the browser and click Submit yourself.")
        print("Script is keeping browser open. Press Ctrl+C in this terminal when you are done.")

        # Keep browser alive until user manually closes
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nCtrl+C received — closing browser.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback; traceback.print_exc()
    finally:
        try:
            driver.quit()
        except:
            pass
        print("Done.")
