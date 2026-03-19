import getpass
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ROOT_ENV)

def main() -> None:
    email = input("Supabase email: ").strip()
    password = getpass.getpass("Supabase password (hidden): ")

    url = os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/token?grant_type=password"
    headers = {
        "apikey": os.environ["SUPABASE_ANON_KEY"],
        "Content-Type": "application/json",
    }
    data = {"email": email, "password": password}

    response = httpx.post(url, headers=headers, json=data, timeout=20)
    print(response.status_code)
    print(response.text)

if __name__ == "__main__":
    main()
