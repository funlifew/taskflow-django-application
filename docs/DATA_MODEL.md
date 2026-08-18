# TaskFlow Data Model

This document summarizes the primary application entities and their relationships.

It intentionally focuses on TaskFlow domain models rather than Django's internal authentication, session and migration tables.

---

## Entity relationship diagram

```mermaid
erDiagram

    USER {
        int id PK
        string username
        string email
        bool email_verified
        string avatar
        text bio
    }

    WORKSPACE {
        int id PK
        string name
        text description
        int owner_id FK
        bool is_archived
    }

    WORKSPACE_MEMBERSHIP {
        int id PK
        int workspace_id FK
        int user_id FK
        string role
    }

    WORKSPACE_INVITATION {
        int id PK
        int workspace_id FK
        int invited_by_id FK
        string email
        string role
        uuid token
        string status
        datetime expires_at
    }

    BOARD {
        int id PK
        int workspace_id FK
        string title
        text description
        int created_by_id FK
        bool is_archived
    }

    COLUMN {
        int id PK
        int board_id FK
        string title
        int position
        int created_by_id FK
        bool is_archived
    }

    TASK {
        int id PK
        int column_id FK
        string title
        text description
        string priority
        string status
        int position
        int assignee_id FK
        int created_by_id FK
        datetime due_at
        bool is_archived
        datetime archived_at
    }

    TASK_COMMENT {
        int id PK
        int task_id FK
        int author_id FK
        text body
        bool is_deleted
        datetime deleted_at
        int deleted_by_id FK
    }

    TASK_ACTIVITY {
        int id PK
        int task_id FK
        int actor_id FK
        string action
        json metadata
        datetime created_at
    }

    NOTIFICATION {
        int id PK
        int recipient_id FK
        int actor_id FK
        string notification_type
        string title
        text message
        string target_url
        json metadata
        bool is_read
        datetime read_at
    }

    USER ||--o{ WORKSPACE : owns

    USER ||--o{ WORKSPACE_MEMBERSHIP : participates
    WORKSPACE ||--o{ WORKSPACE_MEMBERSHIP : contains

    USER ||--o{ WORKSPACE_INVITATION : sends
    WORKSPACE ||--o{ WORKSPACE_INVITATION : creates

    WORKSPACE ||--o{ BOARD : contains
    USER ||--o{ BOARD : creates

    BOARD ||--o{ COLUMN : contains
    USER ||--o{ COLUMN : creates

    COLUMN ||--o{ TASK : contains
    USER ||--o{ TASK : assigned
    USER ||--o{ TASK : creates

    TASK ||--o{ TASK_COMMENT : has
    USER ||--o{ TASK_COMMENT : authors

    TASK ||--o{ TASK_ACTIVITY : records
    USER ||--o{ TASK_ACTIVITY : performs

    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ NOTIFICATION : triggers
```

---

## Workspace membership

Users participate in Workspaces through `WorkspaceMembership`.

Supported roles are:

```text
owner
admin
member
viewer
```

A database uniqueness constraint prevents more than one membership row for the same:

```text
workspace + user
```

Workspace ownership is also stored directly on `Workspace.owner`.

---

## Workspace invitation

An invitation contains:

```text
Workspace
Inviter
Email
Requested role
Unique token
Status
Expiration time
```

Only one active pending invitation is allowed for the same:

```text
workspace + email
```

Invitation states are:

```text
pending
accepted
declined
expired
```

---

## Ordered resources

Column positions are unique among active Columns inside the same Board.

Conceptually:

```text
unique(board, position)
where is_archived = false
```

Task positions follow the same pattern:

```text
unique(column, position)
where is_archived = false
```

Archived rows are intentionally excluded from these conditional uniqueness constraints.

---

## Task archive invariant

Task archive state is constrained so that:

```text
active task
→ archived_at IS NULL
```

and:

```text
archived task
→ archived_at IS NOT NULL
```

Application validation and a database check constraint both protect this rule.

---

## Comment deletion invariant

Visible comments require:

```text
is_deleted = false
deleted_at = NULL
deleted_by = NULL
```

Deleted comments require a deletion timestamp.

The deleting user is retained where available.

---

## Notification read invariant

Notification read state follows:

```text
unread
→ read_at = NULL
```

```text
read
→ read_at IS NOT NULL
```

A database check constraint protects this relationship.

---

## Activity history

`TaskActivity` records important Task events independently from the mutable current Task state.

Examples:

```text
created
updated
status_changed
assignee_changed
moved
reordered
commented
comment_updated
comment_deleted
archived
restored
```

Additional event context is stored in a JSON metadata field.

---

## Indexing highlights

TaskFlow includes indexes for read patterns such as:

```text
Board by workspace/archive state
Column by board/archive state/position
Task by column/archive state/position
Task by assignee/status/due date
Comment by task/deletion state/time
Task activity by task/time
Notification by recipient/read state/time
```

These indexes correspond to common application access patterns rather than being added only for demonstration.