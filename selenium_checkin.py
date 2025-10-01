import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import log
import random

ENDPOINT_URL = "https://cis.ncu.edu.tw/HumanSys/student/stdSignIn"
NCU_CHECKIN_HOST = "https://cis.ncu.edu.tw/HumanSys/student/stdSignIn"

CURRENT_TIME = datetime.now()

# Set Account/Password In Environment Variables -> NCU_PORTAL = account:password
userinfo = os.environ['NCU_PORTAL'].split(":")
ACCOUNT = userinfo[0]
PASSWORD = userinfo[1]

def SeleniumCheckin(projectName, projectTime, requireCheckinHour, signoutMsg):
    driver = None
    try:
        # Setup Chrome options
        chrome_driver_path = r"D:\repos\Checkin-System\chromedriver.exe"

        # Try to find Chrome executable (chrome.exe, NOT chromedriver.exe)
        chrome_binary_path = None
        possible_chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"D:\chrome\chrome-win64\chrome.exe"
        ]

        for path in possible_chrome_paths:
            if os.path.exists(path):
                chrome_binary_path = path
                log.CheckinLog(f"Found Chrome at: {chrome_binary_path}")
                break

        if not chrome_binary_path:
            log.CheckinLog("Chrome binary (chrome.exe) not found. Please install Chrome from https://www.google.com/chrome/")
            return False

        service = Service(executable_path=chrome_driver_path)
        options = webdriver.ChromeOptions()
        options.binary_location = chrome_binary_path  # MUST be chrome.exe path
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)  # 60 second timeout
        wait = WebDriverWait(driver, 30)

        # Step 1: Navigate to endpoint URL
        log.CheckinLog(f"Navigating to {ENDPOINT_URL}")
        driver.get(ENDPOINT_URL)
        log.CheckinLog(f"Page loaded, current URL: {driver.current_url}")
        time.sleep(3)

        # Step 2: Login to NCU Portal
        log.CheckinLog("Attempting to login...")
        try:
            # Wait for and fill in the login form
            username_field = wait.until(EC.presence_of_element_located((By.ID, "inputAccount")))
            password_field = driver.find_element(By.ID, "inputPassword")

            log.CheckinLog("Found login form fields")
            username_field.clear()
            username_field.send_keys(ACCOUNT)
            password_field.clear()
            password_field.send_keys(PASSWORD)
            
            log.CheckinLog("Entered password")

            # Click login button by text
            login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            log.CheckinLog("Clicking login button...")
            login_button.click()
            log.CheckinLog("Login form submitted")
            time.sleep(2)
        except (TimeoutException, NoSuchElementException) as e:
            log.CheckinLog(f"Login form error: {e}")
            return False

        # Step 3: Handle OAuth authorization page
        log.CheckinLog(f"Waiting for OAuth authorization page...")
        time.sleep(2)

        try:
            # Check if we're on the OAuth authorization page
            if 'portal.ncu.edu.tw/oauth' in driver.current_url:
                log.CheckinLog(f"On OAuth page: {driver.current_url}")

                # Wait for and click the "前往" (Go) button
                go_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'].btn.btn-primary")))
                log.CheckinLog("Found '前往' button, clicking...")
                go_button.click()
                log.CheckinLog("Clicked '前往' button")
                time.sleep(2)
            else:
                log.CheckinLog(f"Not on OAuth page, current URL: {driver.current_url}")
        except (TimeoutException, NoSuchElementException) as e:
            log.CheckinLog(f"OAuth page handling error (may be skipped): {e}")

        # Step 4: Wait for redirect to CIS system
        log.CheckinLog(f"Waiting for redirect to CIS system...")
        time.sleep(2)

        # Step 4: Navigate to check-in page
        log.CheckinLog(f"Navigating to {NCU_CHECKIN_HOST}")
        driver.get(NCU_CHECKIN_HOST)
        time.sleep(2)

        # Check if we're still on portal (login failed)
        if 'portal.ncu.edu.tw' in driver.current_url:
            log.CheckinLog("Login failed - still on portal page")
            return False

        log.CheckinLog(f"Current URL: {driver.current_url}")
        log.CheckinLog(f"Page title: {driver.title}")

        # Step 5: Find the project in the table
        try:
            table = wait.until(EC.presence_of_element_located((By.ID, "table1")))
            rows = table.find_elements(By.TAG_NAME, "tr")

            parttime_id = None
            for row in rows[1:]:  # Skip header row
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 6:
                    project_cell = cells[1].text.strip()
                    time_cell = cells[2].text.strip()

                    log.CheckinLog(f"Comparing: '{project_cell}' with '{projectName}'")
                    log.CheckinLog(f"Comparing: '{time_cell}' with '{projectTime}'")

                    if project_cell == projectName and time_cell == projectTime:
                        # Click the check-in link
                        link = cells[5].find_element(By.TAG_NAME, "a")
                        href = link.get_attribute("href")
                        if '=' in href:
                            parttime_id = href.split("=")[-1]
                            log.CheckinLog(f"Found ParttimeUsuallyId: {parttime_id}")
                            link.click()
                            time.sleep(2)
                            break

            if parttime_id is None:
                log.CheckinLog(f"Project not found: {projectName}")
                return False

        except (TimeoutException, NoSuchElementException) as e:
            log.CheckinLog(f"Error finding project table: {e}")
            return False

        # Step 6: Check if signing in or out
        try:
            signin_time_div = driver.find_element(By.ID, "SigninTime")
            signout_time_div = driver.find_element(By.ID, "SignoutTime")

            signin_time = signin_time_div.text.strip()
            signout_time = signout_time_div.text.strip()

            log.CheckinLog(f"SigninTime: '{signin_time}'")
            log.CheckinLog(f"SignoutTime: '{signout_time}'")

            # Check if signin button exists (means not signed in yet)
            try:
                signin_button = driver.find_element(By.ID, "signin")
                is_signin = True
                log.CheckinLog("Found 'signin' button - this is a sign-in operation")
            except NoSuchElementException:
                is_signin = False
                log.CheckinLog("No 'signin' button found - checking for sign-out")

            if is_signin:
                # Signing in
                log.CheckinLog("Clicking '簽到' (Sign-in) button...")
                signin_button.click()
                log.CheckinLog("Clicked sign-in button")
                time.sleep(2)
            else:
                # Signing out - check if enough hours have passed
                if signin_time:
                    signin_hour = int(signin_time.split(":")[0])
                    if CURRENT_TIME.hour - signin_hour < requireCheckinHour:
                        txt = f"簽退時間未滿{requireCheckinHour}小時： " + str(CURRENT_TIME)
                        log.CheckinLog(txt)
                        log.CheckinLog("Not Yet To Signout")
                        return False

                # Fill in signout message in AttendWork textarea
                try:
                    message_field = driver.find_element(By.ID, "AttendWork")
                    message_field.clear()
                    message_field.send_keys(signoutMsg)
                    log.CheckinLog(f"Entered work message in AttendWork: {signoutMsg}")
                except NoSuchElementException:
                    log.CheckinLog("AttendWork field not found")

                # Look for signout button
                try:
                    signout_button = driver.find_element(By.ID, "signout")
                    log.CheckinLog("Clicking '簽退' (Sign-out) button...")
                    signout_button.click()
                    log.CheckinLog("Clicked sign-out button")
                    time.sleep(2)
                except NoSuchElementException:
                    log.CheckinLog("No 'signout' button found")
                    return False

            # Handle confirmation alert if present
            try:
                alert = driver.switch_to.alert
                alert.accept()
                log.CheckinLog("Accepted confirmation alert")
                time.sleep(2)
            except:
                log.CheckinLog("No alert to accept")

            # Log success
            if is_signin:
                txt = '簽到計畫： ' + projectName + '\n' + '簽到時間： ' + str(CURRENT_TIME)
                log.CheckinLog(txt)
                log.CheckinLog("Sign-in successful")
            else:
                txt = '簽退計畫： ' + projectName + '\n' + '簽退時間： ' + str(CURRENT_TIME)
                log.CheckinLog(txt)
                log.CheckinLog("Sign-out successful")

            return True

        except (TimeoutException, NoSuchElementException) as e:
            log.CheckinLog(f"Error during check-in process: {e}")
            return False

    except Exception as e:
        log.CheckinLog(f"Selenium checkin error: {e}")
        return False
    finally:
        # Keep browser open to see the result
        log.CheckinLog("Browser will remain open. Close manually when done.")