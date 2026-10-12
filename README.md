# 🤖 Agentic GitHub Issue Response Pipeline

An event-driven, fault-tolerant backend automation pipeline built with **LangGraph**, **Google Gemini**, **ChromaDB**, **PyGithub**, and **Slack**. The system ingests incoming repository issues, routes them through a stateful multi-step agent for classification and vector context retrieval, enforces a Human-in-the-Loop (HITL) approval gate via Slack, and auto-publishes verified technical responses back to GitHub.

---

## 🏗️ System Architecture & Workflow

```mermaid
flowchart TD
    subgraph Trigger_and_Ingestion ["Ingestion & Trigger"]
        GH_Cron["GitHub Actions Cron (Every 6h)"] --> Ingest["ingest_issues.py (PyGithub)"]
        Manual_Poller["Local Trigger"] --> Ingest
        Ingest -->|Idempotent Check| DB_State[("SQLite issues.db")]
    end

    subgraph LangGraph_Core ["LangGraph Core Agent"]
        DB_State -->|Batch Fetch NEW| Orchestrator["pipeline.py Orchestrator"]
        Orchestrator --> ClassifyNode["Classify Node (Gemini 3.6 Flash)"]
        ClassifyNode --> RetrieveNode["Retrieve Node"]
        ChromaStore[("ChromaDB Vector Store Tool")] -->|Top 3 Chunks| RetrieveNode
        RetrieveNode --> DraftNode["Draft Node (Gemini 3.6 Flash)"]
        DraftNode --> ConfidenceNode["Confidence Check Node"]
    end

    subgraph Human_In_The_Loop ["Human-in-the-Loop & Publishing"]
        ConfidenceNode --> SlackCard["Slack Incoming Webhook (Alert Card)"]
        ConfidenceNode --> ApprovalGate{"Human Review Gate"}
        ApprovalGate -->|Approve| LivePost["PyGithub Comment Publisher"]
        ApprovalGate -->|Reject| MarkRejected["Set Status: REJECTED"]
        ApprovalGate -->|Skip| MarkSkip["Retain Status: NEW"]
        LivePost --> LiveRepo["Target Repository"]
        LivePost --> MarkResolved["Set Status: RESOLVED"]
        MarkResolved --> DB_State
        MarkRejected --> DB_State
    end

    subgraph Fault_Tolerance ["Fault Tolerance & DLQ"]
        RetryWrapper["Tenacity Exponential Backoff (3x)"] -.->|Wraps| DraftNode
        RetryWrapper -.->|Wraps| SlackCard
        RetryWrapper -.->|Wraps| LivePost
        RetryWrapper -->|Max Retries Failed| DLQ["Dead-Letter Queue (FAILED_DLQ)"]
        DLQ --> DB_State
        DLQ --> LogFile[("pipeline.log")]
    end

    subgraph Observability ["Observability & Deployment"]
        DB_State --> Dashboard["Streamlit Dashboard"]
        LogFile --> Dashboard
        Docker["Docker Containerization"] -.->|Packages| Dashboard
    end
```
## MCP Integration: Decoupled Retrieval Architecture

Documentation retrieval is decoupled from the agent runtime and served via an independent Model Context Protocol (MCP) server (`docs-retriever-mcp`) communicating over `stdio`.

### Architecture Comparison
* **Previous:** `[LangGraph Agent] ──> Direct Import ──> ChromaDB (In-Process)`
* **Current:** `[LangGraph Agent] ──> retriever.py (stdio client) ──> [docs-retriever-mcp] ──> ChromaDB`

### Operational Benefits
* **Lightweight Agent Footprint:** Eliminates client-side dependencies on `chromadb` and embedding frameworks in the agent environment.
* **Reusable Tooling:** The same retrieval engine serves this triage agent and external desktop assistants (such as Claude Desktop) simultaneously without modifying server logic.