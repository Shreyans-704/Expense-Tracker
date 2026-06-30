import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.schemas.expense import ParsedExpense

CATEGORY_KEYWORDS = {
    "Food": [
        "lunch", "breakfast", "dinner", "snacks", "snack", "chocolate", "biscuit",
        "biscuits", "chips", "kurkure", "lays", "doritos", "juice", "coffee", "tea",
        "milk", "water", "pizza", "burger", "sandwich", "momos", "roll", "shawarma",
        "biryani", "rice", "roti", "paneer", "chicken", "egg", "eggs", "banana",
        "apple", "orange", "mango", "grapes", "fruit", "fruits", "ice cream",
        "cold drink", "coke", "pepsi", "sprite", "fanta", "groceries"
    ],
    "Transport": [
        "uber", "ola", "rapido", "metro", "bus", "train", "taxi", "cab", "auto",
        "petrol", "diesel", "fuel", "parking", "toll"
    ],
    "Daily Essentials": [
        "handwash", "soap", "shampoo", "conditioner", "toothpaste", "toothbrush",
        "detergent", "surf", "rin", "tide", "wheel", "comfort", "harpic", "phenyl",
        "cleaner", "tissue", "napkin", "bucket", "mug", "broom", "mop", "garbage bag"
    ]
}

def determine_category(item: str) -> str:
    # Remove punctuation for matching, make lowercase
    item_lower = re.sub(r'[^\w\s]', '', item).lower()
    
    # Check whole word match or substring
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in item_lower:
                return cat
    return "Other"

class LocalExpenseParser:
    async def parse(self, text: str) -> Optional[ParsedExpense]:
        # Try to find amount first (any numbers with optional decimal)
        amount_match = re.search(r'\d+(?:\.\d+)?', text)
        if not amount_match:
            return None

        amount_str = amount_match.group(0)

        # Determine item (everything except the amount and common filler words)
        text_without_amount = text.replace(amount_str, '', 1)
        # Remove common filler words and unnecessary/necessary markers
        clean_item = re.sub(r'(?i)\b(spent|on|for|rupees|rs|necessary|unnecessary)\b', '', text_without_amount)
        # Clean up extra spaces and punctuation
        item = re.sub(r'[^\w\s]', '', clean_item).strip()

        # If no item remains after stripping, we can't parse it well
        if not item:
            item = "Unknown"

        category = determine_category(item)

        return ParsedExpense(
            amount=Decimal(amount_str),
            item=item.title(), # Title case for better formatting
            category=category,
            notes="",
            date=datetime.now()
        )
