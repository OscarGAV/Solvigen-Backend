"""
Helper script to generate the bcrypt hash for seed_admin.sql.

Usage:
    python scripts/generate_admin_hash.py

Then copy the printed hash into seed_admin.sql replacing the placeholder.
"""

import bcrypt
import getpass

def main():
    print("=== ITSM-GenIA — Admin Password Hash Generator ===\n")
    password = getpass.getpass("Enter admin password (min 8 chars): ")

    if len(password) < 8:
        print("❌ Password must be at least 8 characters.")
        return

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("❌ Passwords do not match.")
        return

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    print("\n✅ Bcrypt hash generated:\n")
    print(f"    {hashed}\n")
    print("Copy this hash into scripts/seed_admin.sql replacing the placeholder value.")
    print("Then run:  psql -U <user> -d <db_name> -f scripts/seed_admin.sql\n")

if __name__ == "__main__":
    main()