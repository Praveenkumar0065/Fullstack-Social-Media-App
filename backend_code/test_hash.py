import sys
sys.path.append('.')
from auth import hash_password, verify_password

hashed = hash_password("admin123")
print("Hashed:", hashed)
print("Verify:", verify_password("admin123", hashed))
print("Verify wrong:", verify_password("wrong", hashed))
