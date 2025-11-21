# Enterprise AI Agent Platform

# 🚀 Enterprise AI Agent Platform

**Production-ready AI agent platform with FastAPI, LangGraph, and Snowflake**

## ✨ Features

- ✅ **Dual Architecture**: REST API + AI Copilot
- ✅ **LangGraph Agents**: Cyclic reasoning (Plan → Query → Validate → Refine)
- ✅ **Role-Based Access**: Automatic RBAC filtering
- ✅ **File Management**: S3-compatible storage with user scoping
- ✅ **Streaming Support**: Server-Sent Events (SSE)
- ✅ **Generative UI**: CopilotKit widget support
- ✅ **Configurable Checkpointing**: Memory/Redis/Postgres
- ✅ **Enterprise Ready**: 80%+ test coverage, structured logging, observability

## 🏗️ Architecture
```text
REST API Layer          AI Copilot Layer
(Direct Queries)        (Natural Language)
      │                       │
      └───────┬───────────────┘
              ▼
    Snowflake + S3 + Redis
```

## 📦 Getting Started

### 1. Clone and setup

```bash
git clone <your-repo>
cd enterprise-ai-agent
./scripts/setup.sh
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run application

```bash
uv run uvicorn app.main:app --reload
```

### 4. Open API documentation

```bash
open http://localhost:8000/docs
```

## 🧱 Tech Stack

| Component       | Technology                |
|-----------------|---------------------------|
| Framework       | FastAPI + uv              |
| AI Agent        | LangGraph                 |
| OLAP Database   | Snowflake (SQLAlchemy)    |
| OLTP Storage    | Redis / Postgres / Memory |
| File Storage    | S3-compatible             |
| Observability   | LangSmith + structlog     |
| Testing         | pytest (80%+ coverage)    |

## 🎯 Developer Zones

Where to add your code under `app/`:

```text
app/
├── api/v1/endpoints/        # ← Add REST endpoints
├── domain/services/         # ← Add business logic
├── tools/                   # ← Add agent tools
└── prompts/                 # ← Customize prompts
```

## 📚 Documentation

- **Developer Guide** – Start here: `docs/DEVELOPER_GUIDE.md`
- **API Documentation** – Interactive docs at `/docs` when the app is running
- **Agent Development** – See agents, tools, and prompts under `app/agents`, `app/tools`, `prompts/`
- **Testing Guide** – See `tests/` and `scripts/run_tests.sh`

## 🧪 Testing

```bash
# Run all tests
./scripts/run_tests.sh

# Unit tests
uv run pytest tests/unit -m unit

# Integration tests
uv run pytest tests/integration -m integration

# Coverage report
uv run pytest --cov=app --cov-report=html
```

## 🔐 Security

- ✅ Header-based authentication (OAuth upstream)
- ✅ Role-based access control (RBAC)
- ✅ User-scoped data access
- ✅ File permission validation
- ✅ SQL injection prevention (parameterized queries)
