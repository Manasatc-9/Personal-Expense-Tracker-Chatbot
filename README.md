# Personal Expense Tracker Chatbot

A Streamlit expense tracker chatbot that extracts structured expense data from natural language and saves it to Google Sheets.

## Project Structure

- `expense_tracker_app.py` - main Streamlit UI and chat flow
- `expense_extraction.py` - LLM function-calling extraction logic
- `sheets_integration.py` - Google Sheets persistence with `gspread`
- `expense_utils.py` - date parsing and category normalization helpers
- `budget_messages.py` - budgeting and summary messaging
- `credentials.json` - Google service account key file (not version-controlled)
- `.env` - environment variables for API keys and sheet config
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.10+
- Google service account with access to your target Google Sheet

## Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root with:
   ```env
   GROQ_API_KEY=your_groq_api_key
   GROQ_MODEL=llama-3.3-70b-versatile
   SHEET_NAME=Expense Tracker
   SPREADSHEET_ID=your_spreadsheet_id
   ```

3. Place your Google service account JSON key at `credentials.json`.

4. Share the Google Sheet with the service account email found in `credentials.json`.

## Run the App

```bash
streamlit run expense_tracker_app.py
```

Then open the local Streamlit URL shown in the terminal.

## How It Works

- User enters an expense sentence in the chat input.
- `expense_extraction.py` calls the LLM with a function schema to extract:
  - `amount`
  - `category`
  - `date_text`
  - `date`
  - `description`
- If any required fields are missing, the app asks a follow-up question.
- Completed expenses are appended to Google Sheets.

## Example Inputs

- `I bought coffee for 150 rupees today.`
- `Spent 450 on groceries yesterday.`
- `Dinner with friends, 1200.`

## Notes

- Keep `credentials.json` private.
- If you change the Google Sheet name or ID, update `.env` accordingly.
- The app uses Groq/OpenAI-compatible function calling to extract structured data.
