#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional
from time import sleep
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from utils.secrets import get_secret
from config import TMOBILE_CONFIG

@dataclass
class BillEntry:
    phone_number: Optional[str]
    name: Optional[str]
    amount: float

def analyze_tmobile_bill(dry_run=False):
    # Load credentials only when function is called
    USERNAME = get_secret("TMOBILE_USERNAME")
    PASSWORD = get_secret("TMOBILE_PASSWORD")
    # Load Venmo credentials
    VENMO_USERNAME = get_secret("VENMO_USERNAME")
    VENMO_PASSWORD = get_secret("VENMO_PASSWORD")
    VENMO_ACCOUNT_NUMBER = get_secret("VENMO_ACCOUNT_NUMBER")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 1. Navigate to T-Mobile login page
        page.goto("https://account.t-mobile.com/")
        sleep(4)
        page.click('button[aria-label="Close"]')

        # Login
        page.fill('input#usernameTextBox', USERNAME)
        page.click('button:has-text("Next")')
        page.fill('input#passwordTextBox', PASSWORD)
        page.click('button:has-text("Log in")')

        if 'No payment due at this time' in page.content():
            print(f"No payments due at this time")

        page.click('a:has-text("Bill & pay")', timeout=120000)
        page.click('button:has-text("View by line")', timeout=120000)

        # Process bill entries
        bill_entries = []
        summary_blocks = page.locator('div[class*="bb-charge-summary"]')
        count = summary_blocks.count()
        for i in range(count):
            block = summary_blocks.nth(i)
            text = block.inner_text()

            phone_match = re.search(r'\([0-9]+\) [0-9]+-[0-9]+', text)
            name_match = re.search(r'^[A-Za-z]+ ', text)
            dollar_match = re.search(r'\$[0-9.]+', text)

            new_bill_entry = BillEntry(
                            phone_number = phone_match.group(0).strip() if phone_match else None,
                            name = name_match.group(0).strip() if name_match else None,
                            amount = dollar_match.group(0).strip() if dollar_match else None)
            bill_entries.append(new_bill_entry)

        # Get phone number ownership from config
        owners_to_phone_numbers = TMOBILE_CONFIG["owners_to_phone_numbers"]

        # Initialize payment message and totals
        payment_msg = "🤖 Beep beep! Monthly T-Mobile bill time.\n"
        owners_to_total_owed = {}
        for owner, phone_numbers in owners_to_phone_numbers.items():
            owners_to_total_owed[owner] = 0

        print(f"owners_to_total_owed {owners_to_total_owed} 1")

        # Process each bill entry
        ownerToCharge = None
        sharedAccountBalance = None
        totalFinalBalance = None

        for billEntry in bill_entries:
            if billEntry.name.strip() == 'Account':
                print(f"Found shared account balance! {billEntry.amount}")
                sharedAccountBalance = billEntry.amount.replace('$', '')
                continue
            if billEntry.name.strip() == 'Bill':
                print(f"Found TOTAL FINAL account balance! {billEntry.amount}")
                totalFinalBalance = billEntry.amount.replace('$', '')
                continue
            else:
                for owner, phone_numbers in owners_to_phone_numbers.items():
                    if billEntry.phone_number in phone_numbers:
                        ownerToCharge = owner
                        print(f"Charging {owner} with {billEntry}")
                        print(f"- {owner} owns {billEntry.phone_number} for {billEntry.amount}")
                        owners_to_total_owed[owner] = float(billEntry.amount.replace('$', '')) + owners_to_total_owed[owner]
                        break
            if ownerToCharge is None:
                print(f"Oh shit! Did not find an owner for {billEntry}")
            ownerToCharge = None

        # Calculate per-line charges
        num_phone_lines = 0
        for owner, phone_numbers in owners_to_phone_numbers.items():
            num_phone_lines += len(phone_numbers)

        account_total_amount_per_line = float(sharedAccountBalance) / num_phone_lines
        print(f"account_total_amount_per_line {account_total_amount_per_line}")
        print(f"owners_to_phone_numbers {owners_to_phone_numbers}")
        print(f"payment_msg = {payment_msg}")

        # Add the shared account portion to each owner's total
        for owner, total_owed in owners_to_total_owed.items():
            owners_to_total_owed[owner] = owners_to_total_owed[owner] + (account_total_amount_per_line * len(owners_to_phone_numbers[owner]))
        print(owners_to_total_owed)

        # Calculate total after split
        totalAfterSplit = 0
        for owner, total in owners_to_total_owed.items():
            totalAfterSplit += total

        # Print totals and verification
        print("-"*15)
        print("How much each person owes:")
        print("-"*15)
        payment_msg += f"\nThe shared account total is {sharedAccountBalance}"
        payment_msg += f"\nWith {num_phone_lines} lines, that's {account_total_amount_per_line} per line."
        payment_msg += f"\nSo, in total this is how much each person owns:"

        for owner, total in owners_to_total_owed.items():
            print(f"{owner}: ${round(total, 2)}")
            payment_msg += f"\n{owner}:{len(owners_to_phone_numbers[owner])} line(s):${round(total, 2)}"

        print("-"*15)
        payment_msg += f"\nFor a grand total of ${totalFinalBalance}"
        print(f"Total the bill said: {totalFinalBalance}")
        print(f"Total SUM all lines: {totalAfterSplit}")
        print(payment_msg)

        # Verify totals match
        diff = float(totalFinalBalance) - float(totalAfterSplit)
        if float(str(diff).replace('-', '')) > 1:
            print("!!!!!ERROR ERROR ERROR!!!!!")
            print("----> For some reason the diff in amount charged and paid is > $1")
            print("!!!!!ERROR ERROR ERROR!!!!!")

        # Now handle Venmo logic
        page.goto("https://venmo.com/login")

        if "Enter email, mobile, or username" in page.content():
            print("It is asking us to login, lets do it.")
            sleep(2)
            page.fill('input#email', VENMO_USERNAME)
            page.click('button:has-text("Next")')
            print("Done! (with username)")

        sleep(2)
        if "Forgot password" in page.content():
            print("It is asking us for identity, no problem doggy")
            page.fill('input#password', VENMO_PASSWORD)
            page.click('button:has-text("Log in")')

        if "Confirm your identity" in page.content():
            print(f"!! WARNING !! You need to 2FA bro")

        if "To make sure it" in page.content():
            page.click('a:has-text("Confirm another way")')
            if "Enter the full account number" in page.content():
                input = page.locator('#confirm-input')
                input.clear()
                input.fill(VENMO_ACCOUNT_NUMBER)
                page.click('button:has-text("Confirm it")')

        # Get Venmo account mapping from config
        owner_to_venmo = TMOBILE_CONFIG["owner_to_venmo"]

        for owner, venmo_address in owner_to_venmo.items():
            print(f"VENMO: {owner} : {venmo_address} : {owners_to_total_owed[owner]}")

        # Click Pay or Request
        page.click('a:has-text("Pay or Request")')
        sleep(2)

        payment_note = "🤖 Beep beep! " + payment_msg

        # Process Venmo requests
        if dry_run:
            print("\n=== DRY RUN MODE - WOULD SEND THE FOLLOWING VENMO REQUESTS ===")

        for owner, total in owners_to_total_owed.items():
            venmo_username = owner_to_venmo[owner]
            amount = round(total, 2)

            print(f"Preparing Venmo request for {owner} at {venmo_username} for ${amount}")

            # Fill in the Venmo form but don't submit in dry-run mode
            page.fill('input#mui-1', venmo_username)
            page.click('[data-testid="test--resultItem-button"]')

            # Enter amount
            amount_input = page.locator('input[aria-label="Amount"]')
            amount_input.clear()
            amount_input.fill(str(amount))

            # Enter note
            page.fill('#payment-note', f"T-Mobile Bill {datetime.now().strftime('%B %Y')}")

            if dry_run:
                print(f"  Would request ${amount} from {venmo_username} with note: T-Mobile Bill {datetime.now().strftime('%B %Y')}")
                # Reset form for next entry in dry-run mode
                page.click('[data-testid="test--clear-all-button"]')
            else:
                # In real mode, click the request button
                page.click('[data-testid="test--request-button"]')
                # Wait for the request to process
                sleep(2)
                # Go back to start a new request
                page.click('[data-testid="test--back-button"]')

            # For debugging - print what would have happened
            print(f"Owner cell line {owner} owes me {total} and has venmo {venmo_username}")

        if dry_run:
            print("\n=== DRY RUN COMPLETED - NO REQUESTS WERE ACTUALLY SENT ===")

