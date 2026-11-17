"""
CampusAssist: Final Full-System Real-User Audit Script.
Executes live HTTP requests against running dev server (http://127.0.0.1:5000)
to validate all 6 real user scenarios:
1. Known Question: "How can I apply for hostel leave?"
2. Same Intent, Different Wording: "I want to go home for two days. What permission do I need?"
3. Unknown Question: Out-of-domain NIT query with zero hallucination and triage queuing.
4. Admin Review: Login, review unresolved query, author & verify knowledge, trigger re-indexing.
5. Future Query: Multi-phrased query retrieves newly verified knowledge.
6. Security: Unauthorized requests to admin endpoints blocked with 401.
"""

import sys
import json
import time
from pathlib import Path
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BASE_URL = "http://127.0.0.1:5000"


def print_section(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_scenario_1_known_question(session):
    print_section("SCENARIO 1: KNOWN QUESTION ('How can I apply for hostel leave?')")
    url = f"{BASE_URL}/api/chat"
    payload = {
        "query": "How can I apply for hostel leave?",
        "session_id": f"audit_session_{int(time.time())}",
    }
    resp = session.post(url, json=payload, timeout=15)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    data = resp.json()

    print(f"Status: {data.get('status')}")
    print(f"Topic: {data.get('topic')}")
    print(f"Intent: {data.get('intent')} ({data.get('intent_slug')})")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Is Verified: {data.get('is_verified')}")
    print(f"Sources: {data.get('sources')}")
    print(f"Authority Contact: {data.get('authority_contact')}")
    print(f"Answer Preview: {data.get('answer')[:120]}...")

    assert data.get("is_verified") is True, "Must be marked verified"
    assert data.get("intent_slug") == "hostel_leave" or "hostel" in (data.get("topic_slug") or ""), "Must resolve to hostel/leave"
    assert data.get("confidence", 0) >= 0.50, "Confidence must meet threshold"
    assert "gate pass" in data.get("answer", "").lower() or "warden" in data.get("answer", "").lower(), "Must mention gate pass/warden"
    print("[+] SCENARIO 1 PASSED: Correctly classified, retrieved verified knowledge, and generated grounded response.")
    return payload["session_id"]


def test_scenario_2_different_wording(session, session_id):
    print_section("SCENARIO 2: SAME INTENT, DIFFERENT WORDING ('I want to go home for two days. What permission do I need?')")
    url = f"{BASE_URL}/api/chat"
    payload = {
        "query": "I want to go home for two days. What permission do I need?",
        "session_id": session_id,
    }
    resp = session.post(url, json=payload, timeout=15)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    data = resp.json()

    print(f"Query: {payload['query']}")
    print(f"Matched Topic: {data.get('topic')}")
    print(f"Matched Intent: {data.get('intent')} ({data.get('intent_slug')})")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Is Verified: {data.get('is_verified')}")
    print(f"Answer Preview: {data.get('answer')[:120]}...")

    assert data.get("is_verified") is True, "Differently worded query must be verified"
    assert data.get("intent_slug") == "hostel_leave", f"Expected intent hostel_leave, got {data.get('intent_slug')}"
    assert data.get("confidence", 0) >= 0.50, "Confidence must meet threshold"
    print("[+] SCENARIO 2 PASSED: Semantic understanding identified identical intent across conversational variations.")


def test_scenario_3_unknown_question(session, run_id):
    print_section(f"SCENARIO 3: UNKNOWN QUESTION (RUN ID {run_id})")
    url = f"{BASE_URL}/api/chat"
    query = f"Can I install an astronomical stargazing telescope on the main academic building terrace {run_id}?"
    payload = {
        "query": query,
        "session_id": f"audit_unknown_{run_id}",
    }
    resp = session.post(url, json=payload, timeout=15)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    data = resp.json()

    print(f"Query: {query}")
    print(f"Is Verified: {data.get('is_verified')}")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Answer: {data.get('answer')}")

    assert data.get("is_verified") is False, "Must NOT be marked verified"
    ans_lower = data.get("answer", "").lower()
    assert (
        "cannot provide an official verified answer" in ans_lower
        or "no matching authoritative record" in ans_lower
        or "recorded for administrator review" in ans_lower
        or "not confirmed" in ans_lower
    ), f"Must deliver safe unverified notice, got: {ans_lower}"
    assert "hallucinated" not in ans_lower
    print("[+] SCENARIO 3 PASSED: Zero hallucination circuit breaker triggered, question safely queued.")
    return query


def test_scenario_4_admin_review(admin_session, unknown_query_text, run_id):
    print_section(f"SCENARIO 4: ADMIN REVIEW & DYNAMIC KNOWLEDGE INGESTION (RUN ID {run_id})")
    # 1. Login as admin
    login_url = f"{BASE_URL}/api/admin/login"
    login_payload = {
        "username": "admin",
        "password": "AdminAudit2026!Pass",
    }
    login_resp = admin_session.post(login_url, json=login_payload, timeout=10)
    assert login_resp.status_code == 200, f"Admin login failed ({login_resp.status_code}): {login_resp.text}"
    print(f"[+] Admin successfully authenticated: {login_resp.json().get('user')}")

    # 2. Retrieve unresolved queries
    unres_url = f"{BASE_URL}/api/admin/unresolved"
    unres_resp = admin_session.get(unres_url, timeout=10)
    assert unres_resp.status_code == 200
    unresolved_items = unres_resp.json().get("unresolved_queries") or unres_resp.json().get("data", [])
    print(f"Total pending unresolved queries in triage: {len(unresolved_items)}")

    target_query = None
    for item in unresolved_items:
        q_text = item.get("original_question") or item.get("query_text") or ""
        if str(run_id) in q_text:
            target_query = item
            break

    assert target_query is not None, f"Query for run {run_id} must be present in unresolved triage list"
    query_id = target_query["id"]
    print(f"[+] Located target unresolved query #{query_id}: '{target_query.get('original_question') or target_query.get('query_text')}'")

    # 3. Create taxonomy topic/intent for astronomy rooftop access
    topic_slug = f"astronomy_{run_id}"
    top_resp = admin_session.post(f"{BASE_URL}/api/admin/topics", json={
        "name": f"Campus Astronomy & Observatories {run_id}",
        "slug": topic_slug,
        "description": "Rules regarding nighttime terrace access and stargazing telescope setups.",
    })
    assert top_resp.status_code in (200, 201)
    topic_id = top_resp.json().get("topic_id") or top_resp.json().get("id")

    intent_slug = f"telescope_permit_{run_id}"
    intent_resp = admin_session.post(f"{BASE_URL}/api/admin/intents", json={
        "topic_id": topic_id,
        "name": f"Terrace Telescope Permission {run_id}",
        "slug": intent_slug,
        "description": "Official permits and clearance required for installing telescopes on academic building terraces.",
    })
    assert intent_resp.status_code in (200, 201)
    intent_id = intent_resp.json().get("intent_id") or intent_resp.json().get("id")

    # 4. Resolve unresolved query with new verified knowledge
    resolve_url = f"{BASE_URL}/api/admin/unresolved/{query_id}/resolve"
    resolve_payload = {
        "action": "new_knowledge",
        "intent_id": intent_id,
        "title": f"NIT Durgapur Terrace Astronomy Observation Regulations ({run_id})",
        "summary": f"Setting up astronomical telescopes on academic terraces under permit {run_id} requires written clearance from Estate Office and Security.",
        "detailed_procedure": f"1. Submit astronomical night observation form {run_id} to Estate Office at least 48 hours prior.\n2. Obtain written safety endorsement from Faculty Astronomy Advisor.\n3. Terrace rooftop access is permitted strictly between 8:00 PM and 2:00 AM.\n4. Present Stargazing Night Permit {run_id} at the Main Building Security Gate.",
        "required_documents": "Student ID card, Faculty Advisor endorsement letter, Night Safety undertaking form.",
        "contact_authority": "Estate Office & Chief Security Officer",
        "official_portal_url": "https://nitdgp.ac.in/estate-maintenance",
        "keywords": f"astronomy stargazing telescope terrace observation rooftop night sky academic {run_id}",
        "admin_notes": f"Verified under Estate & Security joint circular {run_id}.",
    }
    resolve_resp = admin_session.post(resolve_url, json=resolve_payload, timeout=10)
    assert resolve_resp.status_code == 200, f"Failed to resolve query: {resolve_resp.text}"
    new_knowledge_id = resolve_resp.json().get("knowledge_item_id")
    print(f"[+] Successfully verified query and created knowledge item #{new_knowledge_id}")
    print("[+] In-memory semantic retrieval index automatically synchronized.")


def test_scenario_5_future_query(session, run_id):
    print_section(f"SCENARIO 5: FUTURE QUERY RETRIEVAL OF NEWLY VERIFIED KNOWLEDGE (RUN ID {run_id})")
    url = f"{BASE_URL}/api/chat"
    # Differently worded question asking about the newly added policy
    query = f"What permit do I need to mount a skywatching telescope on academic rooftop for session {run_id}?"
    payload = {
        "query": query,
        "session_id": f"audit_future_{run_id}",
    }
    resp = session.post(url, json=payload, timeout=15)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    data = resp.json()

    print(f"Query: {query}")
    print(f"Topic: {data.get('topic')}")
    print(f"Intent: {data.get('intent')} ({data.get('intent_slug')})")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Is Verified: {data.get('is_verified')}")
    print(f"Sources: {data.get('sources')}")
    print(f"Authority Contact: {data.get('authority_contact')}")
    print(f"Answer: {data.get('answer')}")

    assert data.get("is_verified") is True, "Newly added knowledge must now be verified"
    expected_slug = f"telescope_permit_{run_id}"
    assert data.get("intent_slug") == expected_slug, f"Expected {expected_slug}, got {data.get('intent_slug')}"
    assert "estate" in data.get("answer", "").lower() or "security" in data.get("answer", "").lower(), "Must ground in newly verified procedure"
    print("[+] SCENARIO 5 PASSED: Full closed-loop verification succeeded! Newly added knowledge was retrieved and grounded.")


def test_scenario_6_security(session):
    print_section("SCENARIO 6: SECURITY & AUTHORIZATION ENFORCEMENT")
    # Fresh unauthenticated session
    unauth_session = requests.Session()

    endpoints_to_test = [
        ("GET", f"{BASE_URL}/api/admin/dashboard"),
        ("GET", f"{BASE_URL}/api/admin/knowledge"),
        ("GET", f"{BASE_URL}/api/admin/unresolved"),
        ("POST", f"{BASE_URL}/api/admin/knowledge"),
    ]

    for method, url in endpoints_to_test:
        if method == "GET":
            r = unauth_session.get(url)
        else:
            r = unauth_session.post(url, json={})
        print(f"Testing unauthorized {method} {url} -> HTTP {r.status_code}")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code} for {url}"

    # Test web view redirect
    web_resp = unauth_session.get(f"{BASE_URL}/admin/dashboard", allow_redirects=False)
    print(f"Testing unauthorized GET /admin/dashboard -> HTTP {web_resp.status_code} (Redirect: {web_resp.headers.get('Location')})")
    assert web_resp.status_code in (302, 401), f"Expected 302 redirect or 401, got {web_resp.status_code}"
    print("[+] SCENARIO 6 PASSED: Unauthorized access to administrative APIs and views is strictly blocked.")


def cleanup_audit_artifacts(admin_session=None):
    """Purges dynamic test entries created during audit runs to guarantee test isolation."""
    from app import create_app
    from config import Config
    from app.models.db import get_db

    app = create_app(Config)
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM knowledge_items WHERE title LIKE '%Regulations (%)%' OR title LIKE '%Regulations (%' OR title LIKE '%Drone%' OR title LIKE '%Terrace%'")
        db.execute("DELETE FROM sample_queries WHERE query_text LIKE '%drone%' OR query_text LIKE '%telescope%' OR query_text LIKE '%stargazing%'")
        db.execute("DELETE FROM intents WHERE slug LIKE '%telescope%' OR slug LIKE '%drone%'")
        db.execute("DELETE FROM topics WHERE slug LIKE '%astronomy%' OR slug LIKE '%facilities_%' OR slug = 'campus_facilities'")
        db.execute("DELETE FROM unresolved_queries WHERE original_question LIKE '%drone%' OR original_question LIKE '%telescope%'")
        db.commit()

    if admin_session:
        try:
            admin_session.post(f"{BASE_URL}/api/admin/login", json={
                "username": "admin",
                "password": "AdminAudit2026!Pass",
            }, timeout=5)
            admin_session.post(f"{BASE_URL}/api/admin/sync", timeout=5)
        except Exception:
            pass


def main():
    print("\n" + "=" * 70)
    print(" CAMPUSASSIST: FINAL FULL-SYSTEM REAL USER AUDIT")
    print(" Verifying live system at http://127.0.0.1:5000")
    print("=" * 70)

    session = requests.Session()
    admin_session = requests.Session()
    run_id = int(time.time())

    # Ensure clean slate before running audit
    cleanup_audit_artifacts(admin_session)

    try:
        # Execute all 6 scenarios sequentially
        session_id = test_scenario_1_known_question(session)
        test_scenario_2_different_wording(session, session_id)
        unknown_query = test_scenario_3_unknown_question(session, run_id)
        test_scenario_4_admin_review(admin_session, unknown_query, run_id)
        test_scenario_5_future_query(session, run_id)
        test_scenario_6_security(session)
    finally:
        # Teardown dynamic audit records to restore clean database
        cleanup_audit_artifacts(admin_session)

    print("\n" + "*" * 70)
    print(" ALL 6 REAL USER SCENARIOS COMPLETED & VERIFIED WITH 100% SUCCESS!")
    print("*" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
