# Developer Guide - Enterprise AI Agent Platform

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Architecture Overview](#architecture-overview)
3. [Core vs Developer Zones](#core-vs-developer-zones)
4. [Adding New Features](#adding-new-features)
5. [Testing](#testing)
6. [Best Practices](#best-practices)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- UV package manager
- Snowflake account
- S3-compatible storage
- Enterprise LLM API access

### Setup

```bash
# Clone repository
git clone <repository-url>
cd enterprise-ai-agent

# Run setup
./scripts/setup.sh

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start server
uv run uvicorn app.main:app --reload

# Open API docs
open http://localhost:8000/docs
```

---

## 🏗️ Architecture Overview

```text
┌─────────────────────────────────────────┐
│         FastAPI Application             │
├─────────────────────────────────────────┤
│  🔒 CORE (Non-Touchable)               │
│  - Middleware (auth, logging, tracing) │
│  - Snowflake engine & repository       │
│  - S3 client & file service            │
│  - LangGraph agent framework           │
│  - Widget system                       │
├─────────────────────────────────────────┤
│  🎯 DEVELOPER ZONES                    │
│  - API endpoints (add routes)          │
│  - Domain services (business logic)    │
│  - Agent tools (custom tools)          │
│  - Query templates (SQL queries)       │
└─────────────────────────────────────────┘
```

### Logical Layers

- **Core Layer (`app/core`, `app/middleware`, `app/infrastructure`, `app/agents`, `app/widgets`)**  
  Stable infrastructure: configuration, auth, exceptions, logging, tracing, checkpointing, Snowflake engine, S3 client, LangGraph agent graph, and widget schemas.

- **API Layer (`app/api/v1`)**  
  Versioned HTTP interface. Aggregates endpoint routers (health, agent, stream, files, CopilotKit, etc.).

- **Domain Layer (`app/domain`)**  
  Business logic implemented via services that depend on repositories, tools, and file services.

- **Tools Layer (`app/tools`)**  
  LangChain/LangGraph tools with RBAC-aware `BaseTool` and query templates.

- **Models Layer (`app/models`)**  
  Pydantic request/response models shared across the stack.

---

## 🔐 Core vs Developer Zones

The codebase is intentionally split into **CORE INFRASTRUCTURE** and **DEVELOPER ZONES**.

### Core (Do Not Modify)

These modules are infrastructure contracts. Only change them with strong justification:

- **Config & Auth**
  - `app/core/config.py` – environment-driven settings.
  - `app/core/auth.py` – `UserContext`, `UserRole`, RBAC helpers.
  - `app/core/checkpointer.py` – LangGraph checkpoint backends.
  - `app/core/dependencies.py` – DI for `UserContext`.
  - `app/core/exceptions.py` – `AppException` hierarchy.

- **Middleware**
  - `app/middleware/auth_middleware.py` – header-based auth + `request.state.user`.
  - `app/middleware/logging_middleware.py` – structured request logging.
  - `app/middleware/tracing_middleware.py` – LangSmith tracing metadata.

- **Infrastructure**
  - `app/infrastructure/snowflake/engine.py` – pooled Snowflake SQLAlchemy engine.
  - `app/infrastructure/snowflake/repository.py` – base Snowflake repository.
  - `app/infrastructure/storage/s3_client.py` – S3-compatible client.
  - `app/infrastructure/storage/file_service.py` – user-scoped file service.

- **Agents & Widgets**
  - `app/agents/state.py`, `nodes.py`, `graph_builder.py` – LangGraph core loop.
  - `app/widgets/schemas.py`, `factory.py` – Generative UI widget contracts.

- **API & App Shell**
  - `app/api/v1/endpoints/health.py` – health checks.
  - `app/api/v1/endpoints/stream.py` – SSE streaming.
  - `app/api/v1/endpoints/copilotkit.py` – CopilotKit integration stub.
  - `app/api/v1/router.py` – aggregates endpoints.
  - `app/main.py` – FastAPI app, logging, middleware, router wiring.

- **Prompts & Tool Descriptions**
  - `prompts/system_prompts.yaml`
  - `prompts/tool_descriptions.yaml`

### Developer Zones (Safe to Extend)

Use these extension points for business logic and product features:

- **Domain Services**
  - `app/domain/services/base_service.py`  
    Inherit and add methods in new modules under `app/domain/services/`.

- **API Endpoints**
  - Add new routers in `app/api/v1/endpoints/` and include them from `app/api/v1/router.py`.

- **Agent Tools**
  - `app/tools/base_tool.py` – extend for new LangChain tools.
  - `app/tools/query_templates.py` – register new query templates.

- **Prompts & Tool Config**
  - Extend YAML under `prompts/` for new patterns and tools.

- **Tests**
  - Add unit tests under `tests/unit/` and integration tests under `tests/integration/`.

---

## ✨ Adding New Features

This section shows typical flows for extending the platform.

### 1. Add a New Snowflake Query Template

1. **Define the template** in `app/tools/query_templates.py`:

   ```python
   from app.tools.query_templates import QueryTemplate, QueryParameter, QueryScope, QUERY_TEMPLATES

   QUERY_TEMPLATES["customer_coverage"] = QueryTemplate(
       id="customer_coverage",
       name="Customer Coverage",
       description="Coverage gap by customer",
       sql="""
       SELECT customer_id, customer_name, coverage_gap
       FROM coverage_view
       WHERE customer_id = :customer_id
       """,
       parameters=[
           QueryParameter(
               name="customer_id",
               type="string",
               required=True,
               description="Customer identifier",
           ),
       ],
       scope=QueryScope.USER_ONLY,
       category="coverage",
   )
   ```

2. **Use the template** from a domain service or tool by querying `query_registry`.

### 2. Create a Domain Service

1. **Create a new service** file, e.g. `app/domain/services/sales_service.py`:

   ```python
   from app.domain.services.base_service import BaseService
   from app.core.auth import UserContext

   class SalesService(BaseService):
       def get_sales_kpis(self, user: UserContext):
           self.snowflake_repo.validate_query_permissions(
               user_context=user,
               requires_financial=True,
           )
           query = """
           SELECT metric, value
           FROM sales_kpi_view
           WHERE user_id = :_user_id
           """
           return self.snowflake_repo.execute_query(query, user_context=user)
   ```

### 3. Add a New API Endpoint

1. **Create endpoint module**, e.g. `app/api/v1/endpoints/sales.py`:

   ```python
   from fastapi import APIRouter, Depends
   from app.core.dependencies import UserContextDep
   from app.domain.services.sales_service import SalesService

   router = APIRouter(prefix="/sales", tags=["Sales"])

   @router.get("/kpis")
   async def get_sales_kpis(user: UserContextDep):
       service = SalesService()
       kpis = service.get_sales_kpis(user)
       return {"kpis": kpis}
   ```

2. **Register router** in `app/api/v1/router.py`:

   ```python
   from app.api.v1.endpoints import sales
   api_router.include_router(sales.router)
   ```

### 4. Add an Agent Tool

1. **Create tool class** in `app/tools/sales_tool.py`:

   ```python
   from app.tools.base_tool import BaseTool
   from app.domain.services.sales_service import SalesService

   class SalesKpiTool(BaseTool):
       name = "sales_kpi_tool"
       description = "Fetch sales KPIs for the current user"

       def _run(self, query: str) -> str:
           service = SalesService()
           kpis = service.get_sales_kpis(self.user_context)
           # Format response string for the LLM
           return str(kpis)
   ```

2. **Wire tool into agent** in your orchestration logic (not provided by default; add in a developer module).

---

## ✅ Testing

### Running All Tests

Use the convenience script:

```bash
./scripts/run_tests.sh
```

This will:

- Run **unit tests** (`tests/unit`, `-m unit`).
- Run **integration tests** (`tests/integration`, `-m integration`).
- Generate **coverage** report with threshold 80%.

### Running Tests Manually

```bash
# Unit tests only
uv run pytest tests/unit -m unit -v

# Integration tests only
uv run pytest tests/integration -m integration -v

# Full suite with coverage
uv run pytest --cov=app --cov-report=term-missing
```

### Test Fixtures

Global fixtures are defined in `tests/conftest.py`:

- **User contexts**: `mock_user_context`, `mock_admin_context`, `mock_sales_context`.
- **HTTP clients**: `async_client`, `authenticated_client`.
- **Infra mocks**: `mock_snowflake_engine`, `mock_redis_client`, `mock_s3_client`.
- **Agent & LLM**: `mock_agent_graph`, `mock_llm_response`.
- **Sample data**: `sample_file_data`, `sample_snowflake_data`, `sample_widget_data`.

Reuse these in new tests to keep test code small and focused.

---

## 🧠 Best Practices

### Code Organization

- **Keep core infrastructure stable**  
  Avoid editing `CORE INFRASTRUCTURE` modules unless you are changing platform-wide behavior.

- **Encapsulate business logic in services**  
  Put domain logic in `app/domain/services/`, not in endpoint handlers or tools.

- **Thin endpoints**  
  Endpoints should:
  - Parse inputs (Pydantic models).
  - Resolve `UserContext` via dependencies.
  - Delegate to services.
  - Map service results to response models.

### Security & RBAC

- Always use `UserContextDep` in endpoints that touch user data.
- Use `UserContext` helpers:
  - `is_admin()` for admin-only flows.
  - `can_access_financial_data()` for sensitive KPIs.
- For Snowflake queries, call `validate_query_permissions` if accessing financial data.

### Data Access

- Prefer **query templates** over inline SQL for reusable patterns.
- Use `BaseSnowflakeRepository` and its helpers to apply RBAC filters automatically.
- Limit `SELECT *`; explicitly select only needed columns.

### File Handling

- Always route file operations through `FileService`:
  - Ensures user-scoping (`user_id`-prefixed paths).
  - Centralizes permission checks and metadata.

### Observability

- Use `structlog` for structured logs; include:
  - `user_id`, `thread_id`, and request path where relevant.
- Rely on existing middleware for correlation IDs and tracing.

### Prompts & Tools

- Keep `prompts/system_prompts.yaml` and `prompts/tool_descriptions.yaml` in sync with actual capabilities.
- When adding tools, document them in `tool_descriptions.yaml` so frontends/agents can discover them.

### Performance & Resilience

- Use Snowflake connection pooling via the provided engine (do not create ad-hoc connections).
- For long-running or high-volume workloads, prefer streaming endpoints (`/agent/stream`) where appropriate.

---

This guide should give you a clear map of where to plug in new features while preserving the integrity of the core platform. Focus changes in the **Developer Zones** and treat **Core** modules as shared contracts for all teams.
