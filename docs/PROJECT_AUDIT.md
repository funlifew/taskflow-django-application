# TaskFlow Project Audit

## Current applications

| Application | Responsibility | Status |
|---|---|---|
| accounts | Authentication and profiles | Active |
| core | Shared models and permission mixins | Active |
| dashboard | User dashboard | Active |
| workspaces | Workspaces, memberships and invitations | Active |
| boards | Board lifecycle and presentation | Active |
| columns | Column lifecycle and positioning | Active |
| tasks | Task lifecycle, reordering and collaboration | Active |
| notifications | In-app notification domain | Planned |

## Current concerns

- Large view modules
- Business logic inside views
- Repeated role calculations
- Repeated object-scope queries
- Repeated timestamp updates
- Repeated archive and restore patterns
- Inconsistent formatting
- Large templates and global CSS
- Feature growth without a fixed MVP boundary

## Refactoring priorities

1. Workspaces
2. Boards and Columns
3. Tasks
4. Templates and static assets
5. Notifications foundation

## Non-goals

- Rewriting the project
- Splitting into microservices
- Creating additional Django applications
- Changing the database schema unnecessarily
- Replacing working features
- Introducing asynchronous infrastructure