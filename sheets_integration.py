import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

SHEET_NAME = os.getenv("SHEET_NAME", "Expense Tracker")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_client():
    """Create a Google Sheets client using service account credentials."""
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet():
    """Open the configured Google Sheet and return its first worksheet."""
    client = _get_client()
    if SPREADSHEET_ID:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
    else:
        spreadsheet = client.open(SHEET_NAME)
    return spreadsheet.sheet1


def append_expense(expense):
    """Append an expense row to the Google Sheet.

    The expense dict must include date, amount, category, and description.
    """
    sheet = _get_sheet()
    row = [
        expense["date"],
        expense["amount"],
        expense["category"],
        expense["description"],
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")


def get_monthly_category_total(category):
    """Calculate the total spent in the current month for the provided category."""
    sheet = _get_sheet()
    rows = sheet.get_all_records()
    total = 0.0
    today = datetime.now().date()
    for row in rows:
        try:
            row_date = datetime.fromisoformat(str(row.get("date", ""))).date()
        except ValueError:
            continue
        if row_date.year == today.year and row_date.month == today.month:
            if str(row.get("category", "")).strip().lower() == category.strip().lower():
                try:
                    total += float(row.get("amount", 0))
                except (TypeError, ValueError):
                    continue
    return total