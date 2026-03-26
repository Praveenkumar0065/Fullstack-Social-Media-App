from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

response = client.post("/api/auth/login", json={"email": "admin@socialsphere.app", "password": "admin123"})
print("Status:", response.status_code)
print("Response:", response.json())
