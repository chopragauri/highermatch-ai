import httpx
import sys

try:
    resp = httpx.post("http://localhost:8000/api/auth/login", json={"email":"kartikrjpt123@gmail.com","password":"wrongpassword"})
    print("Status:", resp.status_code)
    print("Body:", resp.text)
except Exception as e:
    print("Failed to connect:", e)
