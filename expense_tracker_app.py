import os
import re
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

print(
    f"expense_tracker_app.py loaded GROQ_API_KEY prefix: "
    f"{os.getenv('GROQ_API_KEY')[:8] if os.getenv('GROQ_API_KEY') else 'None'}"
)


from expense_extraction import (
    extract_expense,
    parse_followup_response,
    generate_followup_question
)

from sheets_integration import (
    append_expense,
    get_monthly_category_total
)

from budget_messages import format_budget_message

from expense_utils import (
    normalize_category,
    parse_date
)


# ==========================================================
# Extract Date Phrase For Display
# ==========================================================

def extract_date_phrase(text):

    text_lower = text.lower()

    date_patterns = [

        r"\b(?:today|yesterday|tomorrow)\b",

        r"\b(?:last|next|this)\s+"
        r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",

        r"\b(?:last|next|this)\s+"
        r"(?:week|month|year)\b",

        r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+"
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))"
        r"(?:,\s*\d{4})?\b",

        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+"
        r"\d{1,2}(?:st|nd|rd|th)?"
        r"(?:,\s*\d{4})?\b"
    ]

    for pattern in date_patterns:

        match = re.search(
            pattern,
            text_lower
        )

        if match:
            return match.group(0)

    return "today"



# ==========================================================
# Streamlit Configuration
# ==========================================================

st.set_page_config(
    page_title="Expense Tracker Chatbot",
    page_icon="💰",
    layout="centered"
)


st.title("💰 Expense Tracker Chatbot")

st.caption(
    "Track your expenses using natural language"
)



# ==========================================================
# API Key Check
# ==========================================================

loaded_key = os.getenv(
    "GROQ_API_KEY"
)


if not loaded_key:

    st.error(
        "GROQ_API_KEY is not loaded from .env"
    )



# ==========================================================
# Session State
# ==========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


if "pending_expense" not in st.session_state:

    st.session_state.pending_expense = None



# ==========================================================
# Display Previous Messages
# ==========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )



# ==========================================================
# Chat Input
# ==========================================================

user_message = st.chat_input(
    "Enter your expense..."
)



# ==========================================================
# Quota Error Detection
# ==========================================================

def is_quota_error(message):

    text = str(message).lower()

    return any(

        keyword in text

        for keyword in [

            "quota exceeded",
            "insufficient quota",
            "resource exhausted",
            "rate limit",
            "429",
            "quota",
            "permission denied"

        ]

    )



# ==========================================================
# Main Chat Logic
# ==========================================================

if user_message:


    st.session_state.messages.append(

        {
            "role": "user",
            "content": user_message
        }

    )


    with st.chat_message("user"):

        st.markdown(
            user_message
        )



    try:


        # --------------------------------------------------
        # If previous expense information is incomplete
        # --------------------------------------------------

        if st.session_state.pending_expense:


            expense, missing = parse_followup_response(

                user_message,

                st.session_state.pending_expense

            )


        else:


            expense, missing = extract_expense(

                user_message

            )



        # --------------------------------------------------
        # Missing fields
        # --------------------------------------------------

        if missing:


            st.session_state.pending_expense = expense


            # LLM generates the follow-up question

            reply = generate_followup_question(

                expense,

                missing

            )



        # --------------------------------------------------
        # Complete Expense
        # --------------------------------------------------

        else:

            if (
                expense.get("amount") is None
                or not expense.get("category")
                or not expense.get("description")
            ):
                st.session_state.pending_expense = expense
                missing_fields = [
                    field
                    for field in ["amount", "category", "description"]
                    if not expense.get(field)
                ]
                reply = generate_followup_question(
                    expense,
                    missing_fields,
                )
            else:
                expense["category"] = normalize_category(
                    expense["category"]
                )


            if not expense.get("original_text"):

                expense["original_text"] = user_message



            date_display = (

                expense.get("date_text")

                or

                extract_date_phrase(
                    expense.get(
                        "original_text",
                        user_message
                    )
                )

            )



            # Normalize Date

            if expense.get("date"):

                expense["date"] = parse_date(

                    expense["date"]

                )


            elif expense.get("date_text"):

                expense["date"] = parse_date(

                    expense["date_text"]

                )


            else:

                expense["date"] = parse_date(

                    expense["original_text"]

                )



            # Save to Google Sheet

            append_expense(

                expense

            )



            # Budget calculation

            previous_total = get_monthly_category_total(

                expense["category"]

            )


            total = (

                previous_total

                +

                float(
                    expense["amount"]
                )

            )



            budget_msg = format_budget_message(

                expense["category"],

                total

            )



            if expense.get("date_text") and expense.get("date"):
                reply = (
                    f"Logged ₹{expense['amount']} for {expense['date_text']} "
                    f"({expense['date']} IST)!"
                )
            else:
                reply = (
                    f"Logged ₹{expense['amount']} for {date_display}!"
                )


            if budget_msg:

                reply += " " + budget_msg



            st.session_state.pending_expense = None



    except Exception as e:


        error_text = str(e)


        if is_quota_error(error_text):

            reply = (

                "❌ Groq API quota/rate limit issue.\n\n"
                "Please check your API key or quota.\n\n"
                f"Details: `{error_text}`"

            )

        else:

            reply = (

                f"❌ Error: {error_text}"

            )



    # ======================================================
    # Assistant Response
    # ======================================================

    st.session_state.messages.append(

        {
            "role": "assistant",
            "content": reply
        }

    )


    with st.chat_message("assistant"):

        st.markdown(
            reply
        )