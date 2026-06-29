# SupportAI - AI Customer Support Assistant

LLM-powered AI customer support assistant with multi-stage ML pipeline: intent classification, semantic FAQ retrieval, sentiment analysis, context-aware response generation, and automated ticket escalation with admin analytics.

---

## Features

- **Intent Classification** -- Classifies messages as billing, technical, account, or general using zero-shot LLM + keyword fallback
- **Semantic FAQ Matching** -- Sentence-Transformer embeddings with cosine similarity; auto-answer (>= 0.90), suggest (0.70-0.89), or pass to LLM
- **Sentiment Analysis** -- Detects positive/neutral/negative sentiment per message; negative triggers escalation offer
- **LLM-Powered Responses** -- Context-aware generation referencing conversation history, intent, FAQ match, and sentiment
- **Template Fallback** -- 20+ response templates ensure the system never fails to respond (even if LLM is down)
- **Sentiment-Triggered Escalation** -- State machine: offer $ \to $ decline (suppressed for 5 messages) $ \to $ auto-escalate
- **Priority Scoring** -- Algorithmic 1-5 score per ticket based on intent base, sentiment severity, and urgent keywords
- **Admin Dashboard** -- 4 KPI cards, stacked bar charts, resolution rate trends, top keywords, dark mode
- **Ticket Management** -- Paginated, filterable, sortable table with CSV export, status lifecycle (open $ \to $ in_progress $ \to $ resolved)
- **FAQ CRUD** -- Admin add/edit/delete with search and intent-based filtering
- **Chat Widget** -- Embeddable 400x600px floating widget for web pages
- **REST API** -- 8 endpoints covering chat, tickets, FAQ, admin metrics, and health
- **Response Quality Feedback** -- 1-5 CSAT rating collected after conversation ends

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Frontend / Dashboard | Streamlit |
| Database | SQLite via SQLAlchemy |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Classifier | `facebook/bart-large-mnli` (zero-shot) |
| Sentiment | `cardiffnlp/twitter-roberta-base-sentiment-latest` |
| LLM | OpenAI / Gemini / any OpenAI-compatible endpoint |
| Runtime | Python 3.11 |
| Validation | Pydantic v2 |
| Charts | Plotly |
| Container | Docker |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your LLM API keys

# 3. Run both services
# Terminal 1 - API server
uvicorn supportai.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Admin dashboard
streamlit run supportai/dashboard.py --server.port 8501
```

Open the API docs at http://localhost:8000/docs and the dashboard at http://localhost:8501.

---

## Project Structure

```
supportai/
├── app.py                    # FastAPI app factory, lifespan, middleware
├── dashboard.py             # Streamlit admin dashboard entry point
├── exceptions.py            # Error classes (ERR-001 to ERR-010)
├── Makefile                 # install / run / test / lint / docker targets
├── Dockerfile               # Multi-stage build (python:3.11-slim)
├── runtime.txt              # python-3.11 (for Streamlit Cloud)
├── requirements.txt         # Python dependencies
├── packages.txt             # System packages (gcc, g++)
├── .env.example             # Environment variable template
├── .streamlit/
│   └── config.toml          # Streamlit theme + server config
├── static/
│   └── style.css            # Dashboard CSS (light/dark theme)
├── widget/
│   └── chat_widget.html     # Embeddable chat widget
├── ml/                      # ML pipeline modules
│   ├── classifier.py        # Intent classifier (zero-shot + keyword)
│   ├── faq_matcher.py       # Semantic FAQ matcher
│   ├── sentiment.py         # Sentiment analyzer
│   ├── pipeline.py          # ChatPipeline orchestrator (10 steps)
│   └── pipeline_config.py   # PipelineConfig dataclass
├── middleware/               # ASGI middleware
│   ├── auth.py              # X-API-Key authentication
│   ├── ratelimit.py         # Token-bucket rate limiting
│   └── logging.py           # Request ID + structured logging
├── routes/                  # FastAPI route modules
│   ├── chat.py              # POST /api/chat
│   ├── tickets.py           # GET/PATCH /api/tickets
│   ├── faq.py               # GET/POST/DELETE /api/faq
│   ├── admin.py             # GET /api/admin/metrics
│   ├── health.py            # GET /api/health
│   └── __init__.py          # Router aggregation
├── pages/                   # Streamlit page modules
│   ├── overview.py          # KPI cards + charts
│   ├── tickets.py           # Ticket list + CSV export
│   ├── conversation.py      # Chat transcript + metadata
│   └── faq_manager.py       # FAQ CRUD
└── tests/                   # Pytest test suite
    ├── test_chat.py
    ├── test_tickets.py
    ├── test_faq.py
    ├── test_health.py
    ├── test_ml.py
    └── conftest.py
```

---

## Configuration

All configuration via environment variables (see `.env.example`):

### LLM

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | -- | OpenAI API key |
| `GEMINI_API_KEY` | -- | Google Gemini API key |
| `LLM_PROVIDER` | `openai` | `openai` or `gemini` |
| `LLM_MODEL_CLASSIFY` | `gpt-4o-mini` | Model for intent classification |
| `LLM_MODEL_SENTIMENT` | `gpt-4o-mini` | Model for sentiment analysis |
| `LLM_MODEL_GENERATE` | `gpt-4o-mini` | Model for response generation |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature |
| `LLM_TIMEOUT_SECONDS` | `5` | API timeout in seconds |
| `LLM_MAX_RETRIES` | `2` | Retry count on transient failure |

### Security

| Variable | Default | Description |
|---|---|---|
| `SUPPORTAI_API_KEYS` | `sk-supportai-test` | Comma-separated valid API keys |
| `ADMIN_USERNAME` | `admin` | Dashboard login username |
| `ADMIN_PASSWORD` | `admin` | Dashboard login password |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///supportai.db` | Database connection string |

### ML Models

| Variable | Default | Description |
|---|---|---|
| `CLASSIFIER_MODEL` | `facebook/bart-large-mnli` | HuggingFace zero-shot classifier |
| `SENTIMENT_MODEL` | `cardiffnlp/twitter-roberta-base-sentiment-latest` | HuggingFace sentiment model |
| `FAQ_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer for embeddings |
| `HF_CACHE_DIR` | -- | HuggingFace model cache directory |

### FAQ Auto-Answer

| Variable | Default | Description |
|---|---|---|
| `FAQ_AUTO_ANSWER_THRESHOLD` | `0.90` | Auto-answer confidence threshold |
| `FAQ_SUGGEST_THRESHOLD` | `0.70` | Suggestion confidence threshold |
| `FAQ_NO_MATCH_THRESHOLD` | `0.30` | No-match threshold |

### Session

| Variable | Default | Description |
|---|---|---|
| `SESSION_EXPIRY_MINUTES` | `30` | Session TTL in minutes |
| `MAX_CONTEXT_MESSAGES` | `10` | Messages in LLM context window |

### Rate Limiting

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_DEFAULT` | `60` | Requests per rate limit window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

### Server

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PORT` | `8000` | API server port |

### Streamlit

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8000` | Backend URL for dashboard |
| `API_KEY` | -- | API key for dashboard requests |
| `STREAMLIT_SERVER_PORT` | `8501` | Dashboard port |

---

## API Overview

| Method | Path | Description | Auth | Rate Limit |
|---|---|---|---|---|
| POST | `/api/chat` | Send message, get AI response | X-API-Key | 60/min |
| GET | `/api/tickets` | List tickets (paginated, filterable) | X-API-Key | 60/min |
| GET | `/api/tickets/{id}` | Get ticket with conversation | X-API-Key | 60/min |
| PATCH | `/api/tickets/{id}` | Update ticket status | X-API-Key | 60/min |
| GET | `/api/faq` | List FAQ entries | X-API-Key | 60/min |
| POST | `/api/faq` | Create FAQ entry | X-API-Key | 30/min |
| DELETE | `/api/faq/{id}` | Delete FAQ entry | X-API-Key | 30/min |
| GET | `/api/admin/metrics` | Dashboard analytics | X-API-Key | 10/min |
| GET | `/api/health` | Service health check | None | 120/min |

Full documentation at `API.md` or http://localhost:8000/docs (Swagger UI).

---

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Connect repo at share.streamlit.io
3. Set `runtime.txt` to `python-3.11`
4. Configure secrets: `API_BASE_URL`, `API_KEY`, etc.
5. Set main entry point: `supportai/dashboard.py`

### Docker

```bash
make docker-build
make docker-run
# API on :8000, Dashboard on :8501
```

### Railway / Render

1. Set build command: `pip install -r requirements.txt`
2. Set start command: `uvicorn supportai.app:app --host 0.0.0.0 --port $PORT`
3. Add environment variables from `.env.example`

### Local

```bash
pip install -r requirements.txt
uvicorn supportai.app:app --host 0.0.0.0 --port 8000
streamlit run supportai/dashboard.py --server.port 8501
```

---

## Testing

```bash
# Run all tests with coverage
make test

# Watch mode
make test-watch

# Lint + typecheck
make lint
make typecheck

# Full check suite
make check-all
```

---

## License

MIT
