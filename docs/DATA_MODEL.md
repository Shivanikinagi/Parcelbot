# Data model (ERD)

All tables are normalised; business identifiers (`ACCT-001`, `ORD-1001`, `TKT-501`) are kept as unique
`code` columns alongside integer surrogate keys used for foreign keys and RBAC scoping.

```mermaid
erDiagram
    ACCOUNTS ||--o{ USERS : "has contacts"
    ACCOUNTS ||--o{ ORDERS : "owns"
    ACCOUNTS ||--o{ TICKETS : "raises"
    ACCOUNTS ||--o{ AGREEMENTS : "signs"
    ACCOUNTS ||--o{ DOCUMENTS : "scopes (agreements)"
    USERS }o--o{ ACCOUNTS : "assigned (support)"
    ORDERS ||--o{ TICKETS : "referenced by"
    USERS ||--o{ CONVERSATIONS : "owns"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
    ACCOUNTS ||--o{ ESCALATIONS : "for"
    TICKETS ||--o{ ESCALATIONS : "about"
    ACCOUNTS ||--o{ FOLLOW_UP_TASKS : "for"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "chunked into"

    ACCOUNTS {
        int id PK
        string code UK
        string name
        string plan
        string status
        string csm
        bool premium_support
        float health_score
    }
    USERS {
        int id PK
        string email UK
        string name
        string role
        int account_id FK
    }
    ORDERS {
        int id PK
        string code UK
        int account_id FK
        string carrier
        string status
        datetime booked_at
        datetime pickup_window_end
        datetime pickup_actual_at
        float shipment_fee_inr
        bool carrier_fault
        bool customer_fault
        datetime cancellation_requested_at
    }
    TICKETS {
        int id PK
        string code UK
        int account_id FK
        int order_id FK
        datetime business_created_at
        string status
        string subject
        string severity
        string historical_resolution
    }
    AGREEMENTS {
        int id PK
        string code UK
        int account_id FK
        string status
        json terms
        text body
    }
    DOCUMENTS {
        int id PK
        string code UK
        string source_type
        string status
        bool internal_only
        int account_id FK
    }
    DOCUMENT_CHUNKS {
        int id PK
        int document_id FK
        text content
        string source_type
        int authority_rank
        bool internal_only
        json embedding
    }
    CONVERSATIONS {
        int id PK
        int user_id FK
        int account_id FK
        string title
        bool pinned
    }
    MESSAGES {
        int id PK
        int conversation_id FK
        string role
        text content
        json meta
    }
    ESCALATIONS {
        int id PK
        string code
        int account_id FK
        int ticket_id FK
        int created_by FK
        string severity
        string status
    }
    FOLLOW_UP_TASKS {
        int id PK
        string code
        int account_id FK
        int ticket_id FK
        int created_by FK
        datetime due_at
    }
    AUDIT_LOGS {
        int id PK
        string request_id
        int actor_user_id
        string action
        string resource_type
        string resource_id
        bool success
        json details
    }
    TOOL_EXECUTIONS {
        int id PK
        string tool_name
        json arguments
        bool success
        int latency_ms
    }
```

## Notes

- **`agreements.terms`** holds machine-readable overrides (SLA targets, cancellation waiver, service-credit
  threshold/amount/cap) that services read directly — the structured twin of the human-readable `body`,
  which is also chunked into the knowledge base.
- **`document_chunks`** denormalises `source_type`, `authority_rank`, `internal_only`, and `account_id`
  so the retriever can rank and RBAC-filter a candidate without extra joins. `embedding` is JSON locally
  and becomes a `pgvector` column in production.
- **`tickets.severity`** is nullable in principle — the source data omits it and the agent classifies it;
  the seed persists the classification for the dashboard.
- **`audit_logs`** is append-only in practice: every state-changing action writes one row, correlated by
  `request_id` to the tool-execution telemetry.
