import os
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# Unlock secrets
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Connect to database
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gemini AI Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Maintenance Toggle
MAINTENANCE_MODE = False