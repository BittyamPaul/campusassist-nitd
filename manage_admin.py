#!/usr/bin/env python3
"""
CampusAssist: Administrator Management CLI.
Utility to provision, list, and reset administrative accounts safely without hardcoded credentials.

Usage:
  python manage_admin.py create --username <username> [--password <password>] [--role <role>] [--display-name <name>]
  python manage_admin.py reset-password --username <username> [--password <password>]
  python manage_admin.py list
"""

import sys
import argparse
import getpass
import secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.models.db import get_db, init_db
from app.models.repositories import (
    get_user_by_username,
    create_user,
    log_audit,
)

VALID_ROLES = ("superadmin", "admin", "reviewer")


def cmd_create(args):
    """Create a new administrator account."""
    conn = get_db()
    init_db()

    username = args.username.strip()
    if not username:
        print("[ERROR] Username cannot be empty.", file=sys.stderr)
        return 1

    role = args.role.strip().lower()
    if role not in VALID_ROLES:
        print(f"[ERROR] Invalid role '{role}'. Allowed roles: {', '.join(VALID_ROLES)}", file=sys.stderr)
        return 1

    existing = get_user_by_username(username, conn=conn)
    if existing:
        print(f"[ERROR] User '{username}' already exists.", file=sys.stderr)
        return 1

    password = args.password
    was_generated = False
    if not password:
        if args.generate_password or not sys.stdin.isatty():
            password = secrets.token_urlsafe(16)
            was_generated = True
        else:
            p1 = getpass.getpass("Enter password for new admin (min 8 chars): ")
            p2 = getpass.getpass("Confirm password: ")
            if p1 != p2:
                print("[ERROR] Passwords do not match.", file=sys.stderr)
                return 1
            password = p1

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.", file=sys.stderr)
        return 1

    display_name = args.display_name or f"Admin ({username})"
    password_hash = generate_password_hash(password)

    user_id = create_user(
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        role=role,
        is_active=1,
        conn=conn,
    )

    log_audit(
        actor_username="CLI",
        actor_role="system",
        action="ADMIN_CREATE",
        target_entity="user",
        target_id=user_id,
        changes_summary=f"Created administrator '{username}' with role '{role}' via CLI.",
        conn=conn,
    )

    print(f"\n[+] Successfully created administrator '{username}' (ID: #{user_id}, Role: '{role}')")
    if was_generated:
        print(f"[*] Generated Password: {password}")
        print("[!] Please save this password securely. It will not be shown again.")
    print()
    return 0


def cmd_reset_password(args):
    """Reset password for an existing administrator account."""
    conn = get_db()
    init_db()

    username = args.username.strip()
    existing = get_user_by_username(username, conn=conn)
    if not existing:
        print(f"[ERROR] User '{username}' not found.", file=sys.stderr)
        return 1

    password = args.password
    was_generated = False
    if not password:
        if args.generate_password or not sys.stdin.isatty():
            password = secrets.token_urlsafe(16)
            was_generated = True
        else:
            p1 = getpass.getpass(f"Enter new password for '{username}' (min 8 chars): ")
            p2 = getpass.getpass("Confirm new password: ")
            if p1 != p2:
                print("[ERROR] Passwords do not match.", file=sys.stderr)
                return 1
            password = p1

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.", file=sys.stderr)
        return 1

    password_hash = generate_password_hash(password)
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (password_hash, existing["id"])
    )
    conn.commit()

    log_audit(
        actor_username="CLI",
        actor_role="system",
        action="ADMIN_PASSWORD_RESET",
        target_entity="user",
        target_id=existing["id"],
        changes_summary=f"Password reset for '{username}' via CLI.",
        conn=conn,
    )

    print(f"\n[+] Password for '{username}' successfully reset.")
    if was_generated:
        print(f"[*] New Generated Password: {password}")
        print("[!] Please save this password securely.")
    print()
    return 0


def cmd_list(args):
    """List all registered administrative accounts."""
    conn = get_db()
    init_db()

    cursor = conn.execute("SELECT id, username, display_name, role, is_active, created_at FROM users ORDER BY id ASC")
    users = cursor.fetchall()

    if not users:
        print("No accounts found in database.")
        return 0

    print(f"\n{'ID':<5} {'Username':<18} {'Role':<14} {'Active':<8} {'Display Name':<25} {'Created At'}")
    print("-" * 90)
    for u in users:
        active_str = "YES" if u["is_active"] else "NO"
        print(f"{u['id']:<5} {u['username']:<18} {u['role']:<14} {active_str:<8} {u['display_name']:<25} {u['created_at']}")
    print("-" * 90)
    print(f"Total Accounts: {len(users)}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CampusAssist Administrative Account Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create
    p_create = subparsers.add_parser("create", help="Create a new administrator account")
    p_create.add_argument("--username", "-u", required=True, help="Administrator username")
    p_create.add_argument("--password", "-p", help="Administrator password (min 8 chars)")
    p_create.add_argument("--role", "-r", default="admin", choices=VALID_ROLES, help="Role (default: admin)")
    p_create.add_argument("--display-name", "-d", help="Display name")
    p_create.add_argument("--generate-password", "-g", action="store_true", help="Generate a random secure password")

    # Reset Password
    p_reset = subparsers.add_parser("reset-password", help="Reset password for an administrator")
    p_reset.add_argument("--username", "-u", required=True, help="Administrator username")
    p_reset.add_argument("--password", "-p", help="New password (min 8 chars)")
    p_reset.add_argument("--generate-password", "-g", action="store_true", help="Generate a random secure password")

    # List
    subparsers.add_parser("list", help="List all administrator accounts")

    args = parser.parse_args()

    if args.command == "create":
        return cmd_create(args)
    elif args.command == "reset-password":
        return cmd_reset_password(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
