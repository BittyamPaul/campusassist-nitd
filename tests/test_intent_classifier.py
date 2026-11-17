"""
Automated Test Suite for Semantic Topic and Intent Classifier.
Verifies multi-phrasing comprehension, confidence gating, candidate ranking,
and zero-code dynamic extensibility through the knowledge system.
"""

import os
import tempfile
import pytest

from app.models.db import init_db, get_db
from app.models.repositories import (
    create_topic,
    create_intent,
    create_knowledge_item,
    add_sample_query,
)
from app.services.classifier.intent_classifier import (
    SemanticIntentClassifier,
    ClassificationResult,
    CandidateIntent,
)
from seed_db import seed_database


@pytest.fixture
def seeded_db():
    """Create a temporary SQLite database pre-populated with verified demo knowledge."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_database(db_path=path)

    yield path

    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass


# ============================================================================
# 1. CORE REQUIREMENT: DIFFERENT QUESTIONS -> SAME HOSTEL LEAVE INTENT
# ============================================================================

def test_hostel_leave_differently_worded_questions(seeded_db):
    """
    Test that distinct student questions expressing the same intent
    all resolve to Topic: Hostel, Intent: Hostel Leave.
    """
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    leave_queries = [
        "How can I apply for hostel leave?",
        "I want to go home for two days. What should I do?",
        "Can I leave the hostel this weekend?",
        "What permission do I need to go home?",
        "Can I go home on Friday night?",
        "How to get gate pass to go home?",
    ]

    for q in leave_queries:
        result = classifier.classify(q, conn=conn)
        assert result.is_confident is True, f"Failed confidence for: '{q}' (score: {result.confidence})"
        assert result.topic_slug == "hostel", f"Expected topic 'hostel' for '{q}', got '{result.topic_slug}'"
        assert result.intent_slug == "hostel_leave", f"Expected intent 'hostel_leave' for '{q}', got '{result.intent_slug}'"
        assert result.confidence >= 0.45

    conn.close()


# ============================================================================
# 2. OTHER HOSTEL DOMAIN INTENT CLASSIFICATIONS
# ============================================================================

def test_hostel_domain_diverse_intents(seeded_db):
    """Test semantic discrimination among different hostel intents."""
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    test_cases = [
        # Room Change
        ("Can I swap rooms with another student in Hall 4?", "hostel", "room_change"),
        ("I want to shift to a different room next semester", "hostel", "room_change"),

        # Mess Problem
        ("The food in the mess tastes terrible and is cold", "hostel", "mess_problem"),
        ("How do I complain about hostel mess hygiene?", "hostel", "mess_problem"),

        # Electricity Issue
        ("The ceiling fan and tube light in my room are broken", "hostel", "electricity_issue"),
        ("Switchboard is sparking in my hostel room", "hostel", "electricity_issue"),

        # Water Supply Issue
        ("Drinking water filter on second floor is leaking and broken", "hostel", "water_issue"),
        ("No running water in our hostel washroom today", "hostel", "water_issue"),

        # Hostel Rules
        ("What time is curfew at night for first years?", "hostel", "hostel_rules"),
        ("Are outside guests allowed inside student hostel rooms?", "hostel", "hostel_rules"),
    ]

    for query, expected_topic, expected_intent in test_cases:
        res = classifier.classify(query, conn=conn)
        assert res.is_confident is True, f"Query '{query}' failed confidence (score: {res.confidence})"
        assert res.topic_slug == expected_topic, f"Query '{query}' expected topic '{expected_topic}', got '{res.topic_slug}'"
        assert res.intent_slug == expected_intent, f"Query '{query}' expected intent '{expected_intent}', got '{res.intent_slug}'"

    conn.close()


# ============================================================================
# 3. ACADEMICS DOMAIN INTENT CLASSIFICATIONS
# ============================================================================

def test_academics_domain_intents(seeded_db):
    """Test classification across academic procedures, exams, and registrations."""
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    test_cases = [
        # Course Registration
        ("How do I register for semester subjects on Chanakya ERP?", "academics", "course_registration"),
        ("Last date for course registration fee payment receipt", "academics", "course_registration"),

        # Examination Regulations
        ("Can I bring a scientific calculator to the mid term examination?", "academics", "examination_rules"),
        ("What are the rules for supplementary exams and backlogs?", "academics", "examination_rules"),

        # Attendance Rules
        ("What is the minimum attendance percentage needed to avoid debarment?", "academics", "attendance_rules"),
        ("Is 75 percent attendance compulsory to write end sem?", "academics", "attendance_rules"),

        # Academic Procedures
        ("How do I get an official bonafide letter for my bank loan?", "academics", "academic_procedures"),
        ("Application process for summer internship NOC", "academics", "academic_procedures"),
    ]

    for query, expected_topic, expected_intent in test_cases:
        res = classifier.classify(query, conn=conn)
        assert res.is_confident is True, f"Query '{query}' failed confidence (score: {res.confidence})"
        assert res.topic_slug == expected_topic, f"Query '{query}' expected topic '{expected_topic}', got '{res.topic_slug}'"
        assert res.intent_slug == expected_intent, f"Query '{query}' expected intent '{expected_intent}', got '{res.intent_slug}'"

    conn.close()


# ============================================================================
# 4. CANDIDATES RANKING & REASONING
# ============================================================================

def test_classifier_candidate_ranking(seeded_db):
    """Test that candidate intents are returned sorted in descending order of confidence."""
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    res = classifier.classify("I want to go home for two days", top_k=3, conn=conn)
    assert len(res.candidates) > 0
    # Verify scores are in descending order
    confidences = [c.confidence for c in res.candidates]
    assert confidences == sorted(confidences, reverse=True)
    # Primary candidate
    assert res.candidates[0].intent_slug == "hostel_leave"

    conn.close()


# ============================================================================
# 5. CONFIDENCE THRESHOLD & UNKNOWN QUERY SAFEGUARD
# ============================================================================

def test_unknown_and_out_of_domain_queries_rejected(seeded_db):
    """
    CRITICAL ANTI-HALLUCINATION TEST:
    Out-of-domain questions with low semantic match must fall below the threshold.
    The classifier must NOT pretend to know the intent.
    """
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    out_of_domain_queries = [
        "What is the capital of France?",
        "Who was Napoleon Bonaparte?",
        "Can you write a poem about quantum physics?",
        "What is the best recipe for baking pizza?",
        "Tell me a funny joke about elephants.",
    ]

    for q in out_of_domain_queries:
        res = classifier.classify(q, conn=conn)
        assert res.is_confident is False, f"Expected unconfident for out-of-domain query '{q}', got confident with {res.confidence}"
        assert res.intent_name is None, f"Expected intent to be None for '{q}', got '{res.intent_name}'"
        assert res.topic_name is None, f"Expected topic to be None for '{q}', got '{res.topic_name}'"
        assert "below threshold" in res.explanation

    conn.close()


# ============================================================================
# 6. DYNAMIC EXTENSIBILITY THROUGH KNOWLEDGE SYSTEM (NO CODE CHANGES)
# ============================================================================

def test_dynamic_intent_addition_without_code_change(seeded_db):
    """
    Test adding a new topic and intent directly in the database.
    After reloading, the classifier must immediately recognize the new intent.
    """
    conn = get_db(seeded_db)
    classifier = SemanticIntentClassifier(confidence_threshold=0.45)
    classifier.train_or_reload(conn=conn)

    # 1. Add a new topic "Health & Medical"
    topic_id = create_topic(
        name="Health Centre",
        slug="health_centre",
        description="NIT Durgapur Medical Unit and emergency ambulance facilities",
        icon="heart",
        conn=conn,
    )

    # 2. Add a new intent "Ambulance Emergency"
    intent_id = create_intent(
        topic_id=topic_id,
        name="Ambulance Emergency",
        slug="ambulance_emergency",
        description="Emergency ambulance service and medical centre contacts",
        conn=conn,
    )

    # 3. Add sample queries for training
    add_sample_query(intent_id, "How to call an ambulance on campus?", conn=conn)
    add_sample_query(intent_id, "Medical emergency contact number for health centre", conn=conn)
    add_sample_query(intent_id, "I need an ambulance to the hostel right now", conn=conn)
    add_sample_query(intent_id, "Doctor emergency hotline NIT Durgapur", conn=conn)

    # 4. Add verified knowledge record
    create_knowledge_item(
        topic_id=topic_id,
        intent_id=intent_id,
        title="NIT Durgapur Emergency Ambulance Service (Demo Record)",
        content="Call the 24/7 Medical Unit Helpline at 0343-2759999 for instant ambulance dispatch.",
        summary="Emergency 24/7 ambulance service available at Health Centre.",
        keywords="ambulance, emergency doctor, medical unit, health centre, hospital",
        source_reference="NIT Durgapur Health Centre Manual (Demo Record)",
        contact_authority="Chief Medical Officer, Health Centre",
        verified_by="NIT Durgapur Health Unit (Demo Record)",
        conn=conn,
    )

    # 5. Dynamically reload the classifier from DB (No code changes!)
    classifier.train_or_reload(conn=conn)

    # 6. Test classifying an unseen variation
    query = "There is a medical emergency in my hall, need an ambulance quickly"
    res = classifier.classify(query, conn=conn)

    assert res.is_confident is True, f"Failed confidence for new dynamic intent (score: {res.confidence})"
    assert res.topic_slug == "health_centre"
    assert res.intent_slug == "ambulance_emergency"
    assert res.intent_name == "Ambulance Emergency"

    conn.close()
