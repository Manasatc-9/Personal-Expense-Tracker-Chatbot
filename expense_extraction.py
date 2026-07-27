import os
import re
import json
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from expense_utils import parse_date, normalize_category

# ==========================================================
# Load Environment Variables
# ==========================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

MODEL_NAME = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

print("=" * 60)
print("Using Groq Model:", MODEL_NAME)
print("=" * 60)

# ==========================================================
# Groq Client
# ==========================================================

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==========================================================
# Function Calling Tool
# ==========================================================

expense_tool = {
    "type": "function",
    "function": {
        "name": "extract_expense",
        "description": "Extract structured expense information from the user's message.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": ["number", "string", "null"],
                    "description": "Expense amount. Omit this field if the amount is unknown."
                },
                "category": {
                    "type": ["string", "null"],
                    "enum": [
                        "Dining",
                        "Transport",
                        "Groceries",
                        "Shopping",
                        "Utilities",
                        "Entertainment",
                        "Other",
                        null
                    ],
                    "description": "Expense category"
                },
                "date_text": {
                    "type": ["string", "null"],
                    "description": "Original date phrase from the user, for example 'last friday'. Omit if no date was provided."
                },
                "date": {
                    "type": ["string", "null"],
                    "description": "Converted expense date in Indian Standard Time (Asia/Kolkata) formatted as YYYY-MM-DD. Omit if no date was provided."
                },
                "description": {
                    "type": ["string", "null"],
                    "description": "Short expense description. Omit if not available."
                }
            },
            "required": []
        }
    }
}

# ==========================================================
# Helper Functions
# ==========================================================

def _clean_amount(amount):

    if amount is None:
        return None

    if isinstance(amount, (int, float)):
        return float(amount)

    if isinstance(amount, str):

        amount = amount.replace("₹", "")
        amount = amount.replace("Rs.", "")
        amount = amount.replace("Rs", "")
        amount = amount.replace("rupees", "")
        amount = amount.replace(",", "")

        m = re.search(r"[0-9]+(?:\.[0-9]+)?", amount)

        if m:
            return float(m.group())

    return None


def _has_explicit_amount(text):
    if not text:
        return False
    return bool(re.search(r"(?:₹|rs\.?|rupees?)\s*\d+|\b\d+(?:\.\d+)?\b", text, re.I))


def _infer_category_from_text(text):
    # Category selection should be decided by the LLM, not by a local object lookup.
    return None


def get_system_prompt():

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""
You are an intelligent Expense Tracker Assistant.

Today's date is {today}.

Your job is to extract expense information.

Use ONLY the function provided.

Fields:

amount
category
date_text
date
description

Rules:

1. Extract amount only if the user explicitly provides a numeric value or currency expression.

2. If the amount cannot be determined, omit the `amount` field from the function output. If you cannot omit it, never  return `amount: null`.

3. If the category cannot be determined, omit the `category` field or return `category: null`.

4. If the date or description cannot be determined, omit those fields or return them as null.

5. Prefer omitting unknown fields, but null is acceptable when a field is not known.

6. If a field is missing, the response may either omit it or set it to null.

7. Example when amount is missing:
   {"category": "Dining", "description": "coffee"}

8. Category should be one of:

Dining
Transport
Groceries
Shopping
Utilities
Entertainment
Other

4. Decide the category from the user's text using the standard domains. Do not rely on a local object list in the app.

5. If the user does not clearly mention a category, infer the best matching domain from the item or description whenever possible. Only leave category blank if it truly does not belong to any standard domain.

6. If the user responds with a short item like "pen", treat that as the expense description and choose the best standard category for it.

7. Return `date_text` exactly as the user expressed it, for example "last friday".

8. Convert that phrase into an expense date in Indian Standard Time (Asia/Kolkata) and return the normalized date in `date` as YYYY-MM-DD.

9. If the user does not provide any date, leave both `date_text` and `date` empty.
    """

def parse_json_response(content):

    if not content:
        return None

    try:
        return json.loads(content)

    except Exception:

        match = re.search(r"\{.*\}", content, re.S)

        if match:

            try:
                return json.loads(match.group())

            except Exception:
                return None

    return None
# ==========================================================
# Call Groq LLM
# ==========================================================

def call_llm(message):

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[

            {
                "role": "system",
                "content": get_system_prompt()
            },

            {
                "role": "user",
                "content": message
            }

        ],

        tools=[expense_tool],

        tool_choice="required",

        temperature=0

    )

    return response


# ==========================================================
# Extract Function Arguments
# ==========================================================

def get_function_args(response):

    try:

        message = response.choices[0].message

        if message.tool_calls:

            tool_call = message.tool_calls[0]

            return json.loads(
                tool_call.function.arguments
            )

        if message.content:

            return parse_json_response(
                message.content
            )

    except Exception as e:

        print("Function Parsing Error:", e)

    return None


# ==========================================================
# Extract Expense
# ==========================================================

def extract_expense(text):

    try:

        response = call_llm(text)

        args = get_function_args(response)

        if not args:

            return {}, [
                "amount",
                "category",
                "description"
            ]

        raw_amount = args.get("amount")
        raw_category = args.get("category")
        raw_date_text = args.get("date_text")
        raw_date = args.get("date")
        raw_description = args.get("description")

        cleaned_amount = _clean_amount(raw_amount)
        if cleaned_amount is not None and not _has_explicit_amount(text):
            cleaned_amount = None
        elif cleaned_amount is None and _has_explicit_amount(text):
            cleaned_amount = _clean_amount(text)

        cleaned_description = (
            raw_description.strip()
            if isinstance(raw_description, str)
            else raw_description
        )
        if cleaned_description == "":
            cleaned_description = None

        normalized_category = None
        if raw_category:
            normalized_category = normalize_category(raw_category)

        expense = {

            "amount":
                cleaned_amount,

            "category":
                normalized_category,

            "date_text":
                raw_date_text,

            "date":
                raw_date or (parse_date(raw_date_text) if raw_date_text else None),

            "description":
                cleaned_description,

            "original_text":
                text

        }

        missing = []

        if expense["amount"] is None:
            missing.append("amount")

        if not expense["category"]:
            missing.append("category")

        if not expense["description"]:
            missing.append("description")

        return expense, missing

    except Exception as e:

        print("Groq Error:", e)

        raise


# ==========================================================
# Generate Natural Follow-up Question
# ==========================================================

def generate_followup_question(expense, missing_fields):

    original_text = expense.get(
        "original_text",
        ""
    )


    prompt = f"""
You are a friendly Expense Tracker Assistant.

Your task is to ask the user for missing expense information.

Current extracted expense information:

{expense}


Original user message:

"{original_text}"


Missing information:

{", ".join(missing_fields)}


Rules:

1. Ask only ONE short and natural question.

2. Do not ask for information that is already available.

3. Mention the existing details when useful.

4. Keep the question conversational.

5. If the amount is already known, refer to it as a plain number without currency symbols.

6. Do not include `$`, `Rs`, or any currency symbol in the question.

Examples:

User:
"I bought coffee"

Extracted:
category = Dining
description = coffee

Missing:
amount

Good question:
"How much did you spend on coffee?"


-----------------------------

User:
"I spent Rs 500"

Extracted:
amount = 500

Missing:
category

Good question:
"What did you spend ₹500 on?"


-----------------------------

User:
"Yesterday I paid money"

Missing:
amount, category, description

Good question:
"Could you tell me how much you spent and what it was for?"


Return ONLY the question.
"""


    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[

            {
                "role": "system",
                "content":
                "You generate natural follow-up questions for an expense tracker."
            },

            {
                "role": "user",
                "content": prompt
            }

        ],

        temperature=0

    )


    return response.choices[0].message.content.strip()

# ==========================================================
# Parse Follow-up Response
# ==========================================================

def parse_followup_response(answer, pending):

    context = f"""
Existing Expense Information

Amount:
{pending.get("amount")}

Category:
{pending.get("category")}

Date:
{pending.get("date_text")}

Description:
{pending.get("description")}

Original User Message:

{pending.get("original_text","")}

User Follow-up:

{answer}

Update ONLY the missing fields.
"""

    expense, missing = extract_expense(context)

    for key in [

        "amount",
        "category",
        "description"

    ]:

        if not expense.get(key):

            expense[key] = pending.get(key)

    if not expense.get("date_text"):
        expense["date_text"] = pending.get("date_text")

    if not expense.get("date"):
        expense["date"] = pending.get("date")

    expense["original_text"] = pending.get(
        "original_text",
        ""
    )

    missing = [

        field

        for field in [

            "amount",
            "category",
            "description"

        ]

        if not expense.get(field)

    ]

    return expense, missing
# ==========================================================
# Ask for Missing Information
# ==========================================================

def ask_for_missing_fields(expense, missing):

    if not missing:
        return None

    return generate_followup_question(
        expense.get("original_text", ""),
        missing
    )


# ==========================================================
# Utility
# ==========================================================

def is_complete(expense):

    return all([
        expense.get("amount") is not None,
        expense.get("category"),
        expense.get("description")
    ])


# ==========================================================
# Local Testing
# ==========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("Expense Tracker using Groq")
    print("=" * 60)

    pending = None

    while True:

        text = input("\nYou : ")

        if text.lower() == "exit":
            break

        # --------------------------------------------------
        # First message
        # --------------------------------------------------

        if pending is None:

            expense, missing = extract_expense(text)

        else:

            expense, missing = parse_followup_response(
                text,
                pending
            )

        # --------------------------------------------------
        # Missing information
        # --------------------------------------------------

        if missing:

            pending = expense

            print()

            print(
                "Bot:",
                generate_followup_question(
                    expense["original_text"],
                    missing
                )
            )

            continue

        pending = None

        print("\nExpense Logged Successfully\n")

        print("Amount      :", expense["amount"])
        print("Category    :", expense["category"])
        print("Date        :", expense["date"])
        print("Description :", expense["description"])