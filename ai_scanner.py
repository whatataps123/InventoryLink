import google.generativeai as genai
import json
import PIL.Image
from config import GEMINI_API_KEY

# Connect to Google Gemini
genai.configure(api_key=GEMINI_API_KEY)

# 🧠 THE FIX: We upgrade to the brand new, active 2.5 model!
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_receipt(image_path, categories=None):
    """Takes an image path, sends it to Gemini, and returns a list of dictionaries."""
    try:
        category_values = categories or [
            "Beverages",
            "Food & Snacks",
            "Rice, Grains & Staples",
            "Cooking & Condiments",
            "Canned & Packaged Goods",
            "Household & Cleaning",
            "Personal Care",
            "Health & Baby Care",
            "Load & Services",
            "School & Office Supplies",
            "Others",
        ]
        category_text = ", ".join(str(category).strip() for category in category_values if str(category).strip())

        with PIL.Image.open(image_path) as img:
            prompt = f"""
            You are a data extraction bot for a Sari-Sari store POS system.
            Analyze this receipt or invoice. Extract the items, quantities, wholesale prices, and best sari-sari store category.
            Use only these category values: {category_text}.
            Return ONLY a valid JSON array of objects, with NO markdown formatting, NO backticks, and NO extra text.
            Format example: [{{"item_name": "Coke 1.5L", "quantity": 2, "wholesale_price": 60.00, "category": "Beverages"}}]
            If you cannot read the image or find no items, return an empty array [].
            """
            
            response = model.generate_content([prompt, img])
            raw_text = response.text.strip()
            
        # Clean up the text in case Gemini accidentally wraps it in markdown blocks
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        # Convert the JSON string into a usable Python list
        extracted_data = json.loads(raw_text.strip())
        return extracted_data
        
    except Exception as e:
        print(f"AI Scanner Error: {e}")
        return []