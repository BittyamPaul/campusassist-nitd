"""
CampusAssist Database Seeding Script.
Initializes the database schema, inserts verified NIT Durgapur demo knowledge,
and creates the initial default administrator account.
"""

import json
import os
import secrets
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

from config import Config
from app.models.db import init_db, get_db
from app.models.repositories import (
    create_topic,
    get_topic_by_slug,
    create_intent,
    get_intent_by_slug,
    create_knowledge_item,
    get_knowledge_by_intent,
    update_knowledge_item,
    add_sample_query,
    create_user,
    get_user_by_username,
    log_audit,
)

BASE_DIR = Path(__file__).resolve().parent
SEED_DATA_PATH = BASE_DIR / "data" / "seed_knowledge.json"


def seed_database(db_path=None, json_path=None, conn=None, admin_password=None):
    """Seed database with verified demo knowledge and admin account."""
    data_file = json_path or SEED_DATA_PATH
    should_close = False

    if conn is None:
        target_db = db_path or Config.DB_PATH
        print(f"[*] Initializing database schema at: {target_db}")
        conn = init_db(target_db)
        should_close = True

    # Check if seed data exists
    if not data_file.exists():
        print(f"[!] Seed data file not found at: {data_file}")
        if should_close:
            conn.close()
        return False

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Seeding knowledge topics and verified demo entries...")
    topics_count = 0
    intents_count = 0
    queries_count = 0

    for topic_data in data.get("topics", []):
        existing_topic = get_topic_by_slug(topic_data["slug"], conn=conn)
        if existing_topic:
            topic_id = existing_topic["id"]
        else:
            topic_id = create_topic(
                name=topic_data["name"],
                slug=topic_data["slug"],
                description=topic_data.get("description", ""),
                icon=topic_data.get("icon", "folder"),
                is_active=1,
                conn=conn,
            )
            topics_count += 1

        for intent_data in topic_data.get("intents", []):
            existing_intent = get_intent_by_slug(intent_data["slug"], conn=conn)
            if existing_intent:
                intent_id = existing_intent["id"]
            else:
                intent_id = create_intent(
                    topic_id=topic_id,
                    name=intent_data["name"],
                    slug=intent_data["slug"],
                    description=intent_data.get("description", ""),
                    is_active=1,
                    conn=conn,
                )
                intents_count += 1

            # Insert or update verified demo knowledge item
            k_data = intent_data.get("knowledge", {})
            if k_data:
                existing_k = get_knowledge_by_intent(intent_id, conn=conn)
                if existing_k:
                    update_knowledge_item(
                        item_id=existing_k["id"],
                        title=k_data["title"],
                        content=k_data.get("content", k_data.get("detailed_procedure", "")),
                        summary=k_data["summary"],
                        keywords=k_data.get("keywords", ""),
                        source_reference=k_data.get("source_reference", "NIT Durgapur Demo Regulations"),
                        contact_authority=k_data.get("contact_authority", ""),
                        official_portal_url=k_data.get("official_portal_url", ""),
                        verified_by=k_data.get("verified_by", "NIT Durgapur Demo Verified"),
                        verification_status=k_data.get("verification_status", "verified"),
                        is_active=k_data.get("is_active", 1),
                        conn=conn,
                    )
                else:
                    create_knowledge_item(
                        topic_id=topic_id,
                        intent_id=intent_id,
                        title=k_data["title"],
                        content=k_data.get("content", k_data.get("detailed_procedure", "")),
                        summary=k_data["summary"],
                        keywords=k_data.get("keywords", ""),
                        source_reference=k_data.get("source_reference", "NIT Durgapur Demo Regulations"),
                        contact_authority=k_data.get("contact_authority", ""),
                        official_portal_url=k_data.get("official_portal_url", ""),
                        verified_by=k_data.get("verified_by", "NIT Durgapur Demo Verified"),
                        verification_status=k_data.get("verification_status", "verified"),
                        version=k_data.get("version", 1),
                        is_active=k_data.get("is_active", 1),
                        conn=conn,
                    )

            # Insert sample query variations for semantic retrieval
            for query_text in intent_data.get("sample_queries", []):
                cur = conn.execute(
                    "SELECT id FROM sample_queries WHERE intent_id = ? AND query_text = ?",
                    (intent_id, query_text)
                )
                if not cur.fetchone():
                    add_sample_query(intent_id=intent_id, query_text=query_text, conn=conn)
                    queries_count += 1

    # Create Initial Admin User securely
    from config import TestingConfig
    admin_username = Config.ADMIN_INITIAL_USERNAME or Config.DEFAULT_ADMIN_USERNAME or "admin"
    existing_admin = get_user_by_username(admin_username, conn=conn)
    if not existing_admin:
        effective_password = admin_password or Config.ADMIN_INITIAL_PASSWORD or Config.DEFAULT_ADMIN_PASSWORD
        if not effective_password and ("PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules):
            effective_password = TestingConfig.DEFAULT_ADMIN_PASSWORD

        if not effective_password:
            effective_password = secrets.token_urlsafe(16)
            print("\n" + "!" * 65)
            print(" [SECURITY NOTICE] No ADMIN_INITIAL_PASSWORD set in environment.")
            print(f" Generated secure random admin password: {effective_password}")
            print(" Please store this password safely or run 'python manage_admin.py'.")
            print("!" * 65 + "\n")

        admin_pass_hash = generate_password_hash(effective_password)
        create_user(
            username=admin_username,
            password_hash=admin_pass_hash,
            display_name="NITD System Admin",
            role="superadmin",
            is_active=1,
            conn=conn,
        )
        log_audit(
            actor_username=admin_username,
            actor_role="superadmin",
            action="SYSTEM_INIT",
            target_entity="system",
            changes_summary="Initial administrator provisioned securely during database initialization.",
            conn=conn,
        )
        print(f"[*] Provisioned administrator: '{admin_username}' (role: superadmin)")
    else:
        print(f"[*] Admin user '{admin_username}' already exists.")

    print(f"[+] Seeding complete! Topics: {topics_count}, Intents: {intents_count}, Sample queries: {queries_count}")
    if should_close:
        conn.close()
    return True


if __name__ == "__main__":
    seed_database()
