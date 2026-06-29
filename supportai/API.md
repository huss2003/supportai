# SupportAI API Reference

**Base URL:** `http://localhost:8000` (local) or your deployed URL.

**Authentication:** All endpoints except `/api/health`, `/docs`, `/redoc`, `/openapi.json`, and `/` require the `X-API-Key` header.

**Rate Limiting:** Token-bucket algorithm per API key. Default: 60 requests / 60s window. Exceptions documented per endpoint.

---

## Error Format

All errors return a consistent JSON body:

```json
{
  "error": "error_type",
  "detail": "Human-readable description.",
  "error_code": "ERR-XXX",
  "request_id": "req-uuid",
  "timestamp": "2026-06-29T12:00:00Z"
}
```

### Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| ERR-001 | 400 | Validation error |
| ERR-002 | 400 | Invalid status transition |
| ERR-003 | 400 | Message exceeds character limit |
| ERR-004 | 401 | Missing API key |
| ERR-005 | 401 | Invalid API key |
| ERR-006 | 404 | Resource not found |
| ERR-007 | 409 | Duplicate resource |
| ERR-008 | 429 | Rate limit exceeded |
| ERR-009 | 500 | Internal server error |
| ERR-010 | 503 | Service unavailable |

---

## POST /api/chat

Send a user message and receive an AI-generated response. The pipeline classifies intent, matches FAQs, analyzes sentiment, and optionally creates tickets.

### Request

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | `string` (uuid) | No | Existing session to continue; omitted starts a new session |
| `message` | `string` | Yes | User message (1-2000 chars, HTML stripped) |
| `metadata` | `object` | No | Extra context: `{ source: string, page_url: string }` |

### Response `200`

| Field | Type | Description |
|---|---|---|
| `session_id` | `string` | Session UUID |
| `reply` | `string` | AI-generated reply text |
| `intent` | `string` | Detected intent: `refund`, `cancel_subscription`, `billing`, `technical_issue`, `account_help`, `feature_request`, `general_inquiry`, `greeting`, `farewell` |
| `intent_confidence` | `number` | 0.0 - 1.0 |
| `faq_match` | `object \| null` | FAQ match result: `{ match_type: string, faq: object, score: number }` or null |
| `sentiment` | `object` | `{ label: string, score: number, normalized_score: number }` |
| `escalation_offered` | `boolean` | Whether escalation was offered to the user |
| `ticket_created` | `object \| null` | Ticket details if one was created, or null |
| `timing_ms` | `number` | Total pipeline processing time in milliseconds |
| `response_method` | `string` | `llm` or `template_fallback` |

### Errors

| Status | Code | When |
|---|---|---|
| 400 | ERR-001 | Message > 2000 chars or missing |
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 429 | ERR-008 | Rate limit exceeded |
| 503 | ERR-010 | Pipeline not initialized |

### Example

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-supportai-test" \
  -d '{
    "message": "I was charged twice for my subscription",
    "metadata": { "source": "web", "page_url": "/pricing" }
  }'
```

```json
{
  "session_id": "a1b2c3d4-...",
  "reply": "I see you're asking about a refund. I've noted this and escalated it to our billing team who will follow up within 24 hours.",
  "intent": "billing",
  "intent_confidence": 0.94,
  "faq_match": null,
  "sentiment": { "label": "negative", "score": 0.82, "normalized_score": -0.47 },
  "escalation_offered": true,
  "ticket_created": { "ticket_id": "TKT-1748912345", "priority_score": 4 },
  "timing_ms": 1420,
  "response_method": "llm"
}
```

---

## GET /api/tickets

List tickets with pagination, filtering, and optional CSV export.

### Query Parameters

| Field | Type | Default | Description |
|---|---|---|---|
| `status` | `string` | -- | Filter: `open`, `in_progress`, `resolved` |
| `intent` | `string` | -- | Filter: `billing`, `technical`, `account`, `general` |
| `priority_min` | `integer` | -- | Min priority (1-5) |
| `priority_max` | `integer` | -- | Max priority (1-5) |
| `escalated` | `boolean` | -- | Filter escalated tickets |
| `page` | `integer` | 1 | Page number (>= 1) |
| `per_page` | `integer` | 50 | Items per page (1-100) |
| `export` | `string` | -- | Set to `csv` to download as CSV |

### Response `200`

| Field | Type | Description |
|---|---|---|
| `tickets` | `array` | List of ticket objects |
| `pagination` | `object` | `{ page, per_page, total_items, total_pages }` |

Each ticket:

| Field | Type | Description |
|---|---|---|
| `ticket_id` | `string` | Unique ticket ID |
| `session_id` | `string` | Associated session |
| `intent` | `string` | Detected intent |
| `priority_score` | `integer` | 1-5 priority |
| `priority_breakdown` | `object` | Per-factor priority breakdown |
| `status` | `string` | `open`, `in_progress`, `resolved` |
| `escalated` | `boolean` | Escalation flag |
| `created_at` | `datetime` | ISO 8601 |
| `updated_at` | `datetime` | ISO 8601 |
| `resolved_at` | `datetime \| null` | ISO 8601 or null |

### Errors

| Status | Code | When |
|---|---|---|
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 429 | ERR-008 | Rate limit exceeded |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl "http://localhost:8000/api/tickets?status=open&page=1&per_page=50" \
  -H "X-API-Key: sk-supportai-test"
```

```json
{
  "tickets": [
    {
      "ticket_id": "TKT-1748912345",
      "session_id": "a1b2c3d4-...",
      "intent": "billing",
      "priority_score": 4,
      "priority_breakdown": { "intent_base": 3, "sentiment_boost": 1, "keyword_boost": 0 },
      "status": "open",
      "escalated": true,
      "created_at": "2026-06-29T10:00:00Z",
      "updated_at": "2026-06-29T10:00:00Z",
      "resolved_at": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_items": 1,
    "total_pages": 1
  }
}
```

---

## GET /api/tickets/{ticket_id}

Get a single ticket with full conversation transcript.

### Path Parameters

| Field | Type | Description |
|---|---|---|
| `ticket_id` | `string` | Ticket ID |

### Response `200`

| Field | Type | Description |
|---|---|---|
| `ticket_id` | `string` | Unique ticket ID |
| `session_id` | `string` | Associated session |
| `intent` | `string` | Detected intent |
| `priority_score` | `integer` | 1-5 priority |
| `priority_breakdown` | `object` | Per-factor breakdown |
| `status` | `string` | `open`, `in_progress`, `resolved` |
| `escalated` | `boolean` | Escalation flag |
| `conversation` | `array` | Chronological messages with role, content, intent, sentiment, timing |
| `created_at` | `datetime` | ISO 8601 |
| `updated_at` | `datetime` | ISO 8601 |
| `resolved_at` | `datetime \| null` | ISO 8601 or null |

### Errors

| Status | Code | When |
|---|---|---|
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 404 | ERR-006 | Ticket not found |
| 429 | ERR-008 | Rate limit exceeded |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl "http://localhost:8000/api/tickets/TKT-1748912345" \
  -H "X-API-Key: sk-supportai-test"
```

```json
{
  "ticket_id": "TKT-1748912345",
  "session_id": "a1b2c3d4-...",
  "intent": "billing",
  "priority_score": 4,
  "priority_breakdown": { "intent_base": 3, "sentiment_boost": 1, "keyword_boost": 0 },
  "status": "open",
  "escalated": true,
  "conversation": [
    { "role": "user", "content": "I was charged twice", "intent": "billing", "sentiment": "negative" },
    { "role": "assistant", "content": "I see you're asking about a refund...", "method": "llm" }
  ],
  "created_at": "2026-06-29T10:00:00Z",
  "updated_at": "2026-06-29T10:00:00Z",
  "resolved_at": null
}
```

---

## PATCH /api/tickets/{ticket_id}

Update a ticket's status with transition validation.

### Path Parameters

| Field | Type | Description |
|---|---|---|
| `ticket_id` | `string` | Ticket ID |

### Request

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | `string` | Yes | `open`, `in_progress`, or `resolved` |

### Valid Transitions

| From | To |
|---|---|
| `open` | `in_progress` |
| `in_progress` | `resolved`, `open` |
| `resolved` | `in_progress` |

### Response `200`

| Field | Type | Description |
|---|---|---|
| `ticket_id` | `string` | Ticket ID |
| `status` | `string` | New status |
| `updated_at` | `datetime` | ISO 8601 |
| `resolved_at` | `datetime \| null` | Set on `resolved`, null otherwise |

### Errors

| Status | Code | When |
|---|---|---|
| 400 | ERR-002 | Invalid status transition |
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 404 | ERR-006 | Ticket not found |
| 429 | ERR-008 | Rate limit exceeded |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl -X PATCH "http://localhost:8000/api/tickets/TKT-1748912345" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-supportai-test" \
  -d '{ "status": "in_progress" }'
```

```json
{
  "ticket_id": "TKT-1748912345",
  "status": "in_progress",
  "updated_at": "2026-06-29T12:00:00Z",
  "resolved_at": null
}
```

---

## GET /api/faq

List FAQ entries with search and intent-based filtering.

### Query Parameters

| Field | Type | Default | Description |
|---|---|---|---|
| `intent` | `string` | -- | Filter: `billing`, `technical`, `account`, `general` |
| `search` | `string` | -- | Full-text search (min 2 chars) |
| `page` | `integer` | 1 | Page number (>= 1) |
| `per_page` | `integer` | 50 | Items per page (1-100) |

### Response `200`

| Field | Type | Description |
|---|---|---|
| `faqs` | `array` | List of FAQ objects |
| `pagination` | `object` | `{ page, per_page, total_items, total_pages }` |

Each FAQ:

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | FAQ ID |
| `question` | `string` | Question text |
| `answer` | `string` | Answer text |
| `intent_tags` | `array` | Intent tags (`billing`, `technical`, `account`, `general`) |
| `created_at` | `datetime` | ISO 8601 |

### Errors

| Status | Code | When |
|---|---|---|
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 429 | ERR-008 | Rate limit exceeded |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl "http://localhost:8000/api/faq?intent=billing&page=1&per_page=20" \
  -H "X-API-Key: sk-supportai-test"
```

```json
{
  "faqs": [
    {
      "id": 1,
      "question": "How do I get a refund?",
      "answer": "You can request a refund from your account settings under Billing > Refunds. Refunds are processed within 5-7 business days.",
      "intent_tags": ["billing"],
      "created_at": "2026-06-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 1,
    "total_pages": 1
  }
}
```

---

## POST /api/faq

Create a new FAQ entry. Question must be unique.

### Request

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | `string` | Yes | 10-500 chars, unique |
| `answer` | `string` | Yes | 20-2000 chars |
| `intent_tags` | `array` | Yes | 1+ of: `billing`, `technical`, `account`, `general` |

### Response `201`

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | FAQ ID |
| `question` | `string` | Question text |
| `answer` | `string` | Answer text |
| `intent_tags` | `array` | Intent tags |
| `created_at` | `datetime` | ISO 8601 |

### Errors

| Status | Code | When |
|---|---|---|
| 400 | ERR-001 | Validation failed |
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 409 | ERR-007 | Duplicate question |
| 429 | ERR-008 | Rate limit exceeded (30/min) |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl -X POST "http://localhost:8000/api/faq" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-supportai-test" \
  -d '{
    "question": "How do I reset my password?",
    "answer": "Go to Settings > Security > Reset Password. Enter your email to receive a reset link.",
    "intent_tags": ["account"]
  }'
```

```json
{
  "id": 2,
  "question": "How do I reset my password?",
  "answer": "Go to Settings > Security > Reset Password. Enter your email to receive a reset link.",
  "intent_tags": ["account"],
  "created_at": "2026-06-29T12:00:00Z"
}
```

---

## DELETE /api/faq/{faq_id}

Delete a FAQ entry by ID.

### Path Parameters

| Field | Type | Description |
|---|---|---|
| `faq_id` | `integer` | FAQ ID |

### Response `204`

No content body on success.

### Errors

| Status | Code | When |
|---|---|---|
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 404 | ERR-006 | FAQ not found |
| 429 | ERR-008 | Rate limit exceeded (30/min) |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl -X DELETE "http://localhost:8000/api/faq/2" \
  -H "X-API-Key: sk-supportai-test"
```

Response: `204 No Content`

---

## GET /api/admin/metrics

Dashboard analytics with KPIs, trends, and time-series data.

### Query Parameters

| Field | Type | Default | Description |
|---|---|---|---|
| `days` | `integer` | 7 | Lookback period (1-90) |

### Response `200`

| Field | Type | Description |
|---|---|---|
| `total_conversations` | `integer` | Total conversations in period |
| `auto_resolved` | `integer` | Auto-resolved by FAQ/LLM |
| `escalated` | `integer` | Escalated to human |
| `resolution_rate` | `number` | Auto-resolved / total (percentage) |
| `avg_handling_time_seconds` | `number` | Average handling time |
| `csat_score` | `number \| null` | CSAT score (1-5) or null |
| `trends` | `object` | Per-metric trend: `{ value, direction, percentage_change }` |
| `intent_breakdown` | `array` | Per-intent counts and percentages |
| `daily_volume` | `array` | Per-day volume by intent (last N days) |
| `resolution_rate_over_time` | `array` | Per-day resolution rate |
| `top_keywords` | `array` | Top 10 keywords from messages |

### Errors

| Status | Code | When |
|---|---|---|
| 401 | ERR-004 / ERR-005 | Missing or invalid API key |
| 429 | ERR-008 | Rate limit exceeded (10/min) |
| 503 | ERR-010 | Database not available |

### Example

```bash
curl "http://localhost:8000/api/admin/metrics?days=7" \
  -H "X-API-Key: sk-supportai-test"
```

```json
{
  "total_conversations": 142,
  "auto_resolved": 98,
  "escalated": 44,
  "resolution_rate": 69.0,
  "avg_handling_time_seconds": 45.2,
  "csat_score": 4.2,
  "trends": {
    "total_conversations": { "value": 142, "direction": "up", "percentage_change": 12.3 },
    "resolution_rate": { "value": 69.0, "direction": "up", "percentage_change": 3.1 },
    "avg_handling_time_seconds": { "value": 45.2, "direction": "down", "percentage_change": -8.5 }
  },
  "intent_breakdown": [
    { "intent": "billing", "count": 45, "percentage": 31.7 },
    { "intent": "technical", "count": 38, "percentage": 26.8 }
  ],
  "daily_volume": [
    { "date": "2026-06-23", "billing": 6, "technical": 5, "account": 3, "general": 4, "total": 18 }
  ],
  "resolution_rate_over_time": [
    { "date": "2026-06-23", "resolved": 13, "total": 18, "rate": 72.2 }
  ],
  "top_keywords": [
    { "keyword": "refund", "count": 28 },
    { "keyword": "error", "count": 22 }
  ]
}
```

---

## GET /api/health

Service health check. No authentication required.

### Response `200`

| Field | Type | Description |
|---|---|---|
| `status` | `string` | `healthy`, `degraded`, or `unhealthy` |
| `version` | `string` | API version |
| `uptime_seconds` | `number` | Seconds since startup |
| `models_loaded` | `boolean` | ML pipeline loaded |
| `db_connected` | `boolean` | Database connected |
| `sessions_active` | `integer` | Active sessions count |
| `tickets_open` | `integer` | Open tickets count |
| `memory_usage_mb` | `number` | RSS memory in MB |

### Rate Limit

120 requests per minute (no auth needed).

### Example

```bash
curl "http://localhost:8000/api/health"
```

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 84600.0,
  "models_loaded": true,
  "db_connected": true,
  "sessions_active": 12,
  "tickets_open": 3,
  "memory_usage_mb": 245.6
}
```
