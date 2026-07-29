# TaskFlow Architecture

TaskFlow is a Django monolith organized around six product domains:

1. Accounts
2. Workspaces
3. Boards
4. Columns
5. Tasks
6. Notifications

## Domain hierarchy

User
└── Workspace
    ├── Membership
    ├── Invitation
    └── Board
        └── Column
            └── Task
                ├── Comment
                ├── Activity
                └── Notification event

## Application rules

### Views

Views handle:

- HTTP requests and responses
- redirects
- Django messages
- form binding
- template context

Views must not contain complex transactional business logic.

### Forms

Forms handle:

- input validation
- user-facing validation errors
- conversion of request values

### Services

Services handle:

- database mutations
- transactions
- row locking
- lifecycle operations
- cross-model updates

### Selectors

Selectors handle:

- complex read queries
- annotations
- prefetching
- reusable filtered querysets

### Mixins

Mixins handle:

- access control
- URL-scoped object retrieval
- shared role checks

### Models

Models handle:

- database structure
- model-level invariants
- simple QuerySet helpers

## Scope rule

No new feature may be added before its relationship to the MVP scope is documented.

Refactoring must preserve:

- existing URLs
- existing permissions
- existing database behavior
- existing tests
- existing templates unless explicitly changed