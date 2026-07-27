import json
from expense_extraction import expense_tool
print(json.dumps(expense_tool['function']['parameters']['properties']['amount'], indent=2))
print('---')
print(json.dumps(expense_tool['function']['parameters']['properties']['category'], indent=2))
print('---')
print(json.dumps(expense_tool['function']['parameters']['properties']['date_text'], indent=2))
print('---')
print(json.dumps(expense_tool['function']['parameters']['properties']['date'], indent=2))
print('---')
print(json.dumps(expense_tool['function']['parameters']['properties']['description'], indent=2))
