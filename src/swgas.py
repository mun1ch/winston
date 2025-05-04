#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
from utils.secrets import get_secret
from datetime import datetime
from time import sleep

def pay_southwest_gas_bill():
    # Load credentials only when function is called
    USERNAME = get_secret("SWGAS_USERNAME")
    PASSWORD = get_secret("SWGAS_PASSWORD")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=True after it's stable
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Go directly to login page
        page.goto("https://myaccount.swgas.com/Portal/#/login", wait_until="networkidle")

        # Step 2: Wait for username input field to appear and be visible
        page.wait_for_selector('input#username', state="visible", timeout=60000)

        # Step 3: Fill username and password
        page.fill('input#username', USERNAME)
        page.fill('input#password', PASSWORD)

        # Step 4: Click the login button
        page.click('button#login-button')

        # Step 5: Wait for dashboard page to confirm successful login
        sleep(5)

        print("✅ Successfully logged into Southwest Gas")

        # Get due date
        due_date_text = page.inner_text('span.dueDate').strip()
        due_date = datetime.strptime(due_date_text, "%b %d,%Y")

        # Compare
        dueToday = False
        today = datetime.today().date()
        if due_date.date() == today:
            print("✅ It's due today!")
            dueToday = True
        else:
            print(f"❌ Not due today. Due: {due_date.date()} Today: {today}")

        last_bill_a = page.locator('a[aria-label*="last bill"]')
        # Example: get its aria-label text
        last_bill_text = last_bill_a.get_attribute('aria-label')
        last_bill_text = last_bill_a.get_attribute('aria-label')

        print(last_bill_text) 
        print(f"Current balance {page.inner_text('span.currentBalance')}")

        page.click('a[aria-label="Click to pay current bill"]')
        page.click('button:has-text("Next")')
        page.check('#termsAndConditionCheckbox')
        sleep(5)

        if dueToday:
            print("✅ It's due today!, submitting payment")
            page.click('button:has-text("Submit Payment")')
        else:
            print("❌ Not due today, paying later")
        sleep(15)
        browser.close()

if __name__ == "__main__":
    pay_southwest_gas_bill()

