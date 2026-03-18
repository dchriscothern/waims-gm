import os
import getpass

import httpx
from dotenv import load_dotenv

load_dotenv()

email = input("Supabase email: ").strip()
password = getpass.getpass("Supabase password (hidden): ")

url = os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/token?grant_type=password"
headers = {"apikey": os.environ["SUPABASE_ANON_KEY"], "Content-Type": "application/json"}
data = {"email": email, "password": password}

r = httpx.post(url, headers=headers, json=data, timeout=20)
print(r.status_code)
print(r.text)