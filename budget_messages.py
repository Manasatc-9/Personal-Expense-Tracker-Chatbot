# This module defines budget limits per category and formats a budget warning

CATEGORY_BUDGETS = {
    "Dining": 10000,
    "Transport": 8000,
    "Groceries": 12000,
    "Shopping": 10000,
    "Utilities": 9000,
    "Entertainment": 7000,
    "Other": 8000,
}

# message when the monthly spend approaches or exceeds the category threshold.
def format_budget_message(category, total):
    limit = CATEGORY_BUDGETS.get(category)
    if not limit:
        return ""
    percent = int((total / limit) * 100) if limit else 0
    percent = min(percent, 100)
    return f"You've used {percent}% of your {category.lower()} budget this month."