# CampusAssist REST API Documentation

Base URL: `http://127.0.0.1:5000/api`

---

## Public Student Endpoints

### 1. Health Check
- **Endpoint**: `GET /api/health`
- **Description**: Returns application health, institution info, and version.
- **Response**:
```json
{
  "status": "healthy",
  "app": "CampusAssist",
  "institution": "National Institute of Technology Durgapur",
  "department": "Computer Science & Engineering",
  "owner": "Bittyam Paul",
  "version": "1.0.0"
}
```

### 2. Suggested Queries & Topics
- **Endpoint**: `GET /api/suggestions`
- **Description**: Fetches popular starter questions and categories for the student interface.

### 3. All Topics & Intents
- **Endpoint**: `GET /api/topics`
- **Description**: Returns full hierarchy of verified knowledge domains and intents.

### 4. Chat Query Processing
- **Endpoint**: `POST /api/chat`
- **Payload**:
```json
{
  "query": "I want to go home for two days. What should I do?",
  "session_id": "session_abc123"
}
```
- **Response**:
```json
{
  "status": "success",
  "answer": "...",
  "is_verified": true,
  "topic": "Hostel",
  "intent": "Hostel Leave",
  "confidence": 0.88,
  "sources": ["NIT Durgapur Chief Warden Office"]
}
```

### 5. Chat Interaction Feedback
- **Endpoint**: `POST /api/feedback`
- **Payload**:
```json
{
  "chat_log_id": 42,
  "feedback": "helpful"
}
```

---

## Protected Administrator Endpoints (Requires Auth Session)

### 1. Dashboard Metrics
- **Endpoint**: `GET /api/admin/stats`

### 2. Knowledge Items CRUD
- `GET /api/admin/knowledge`: List verified knowledge articles
- `GET /api/admin/knowledge/<id>`: Get single knowledge item
- `POST /api/admin/knowledge`: Create new verified knowledge item
- `PUT /api/admin/knowledge/<id>`: Update knowledge item
- `DELETE /api/admin/knowledge/<id>`: Delete knowledge item

### 3. Unresolved Queries Triage
- `GET /api/admin/unresolved?status=pending`: List unverified queries
- `POST /api/admin/unresolved/<id>/resolve`: Triage query (actions: `map_intent`, `new_knowledge`, `ignore`)

### 4. Administrative Audit Trail
- `GET /api/admin/audit?limit=25`: Fetch chronological audit history
