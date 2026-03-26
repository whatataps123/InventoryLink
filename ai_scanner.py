import google.generativeai as genai
import json
import PIL.Image
from config import GEMINI_API_KEY

# Connect to Google Gemini
genai.configure(api_key=GEMINI_API_KEY)

# 🧠 THE FIX: We upgrade to the brand new, active 2.5 model!
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_receipt(image_path):
    """Takes an image path, sends it to Gemini, and returns a list of dictionaries."""
    try:
        with PIL.Image.open(image_path) as img:
            prompt = """
            You are a data extraction bot for a Sari-Sari store POS system.
            Analyze this receipt or invoice. Extract the items, quantities, and wholesale prices.
            Return ONLY a valid JSON array of objects, with NO markdown formatting, NO backticks, and NO extra text.
            Format example: [{"item_name": "Coke 1.5L", "quantity": 2, "wholesale_price": 60.00}]
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