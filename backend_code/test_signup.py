from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
res = client.post("/api/auth/signup", json={"name": "Johan", "email": "johan@example.com", "password": "password123"})
print(res.status_code)
print(res.json())
