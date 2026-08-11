<div align="center">

# ✨ TaskFlow

### Persian-first collaborative task management built with Django

<p> A portfolio project focused on backend architecture, transactional business logic, role-based access control, testing, interactive taًsk workflows, and modern RTL UI/UX. </p>






\

<br>

[Overview](#-overview) ·
[Features](#-features) ·
[Architecture](#-architecture) ·
[Stack](#-technology-stack) ·
[Setup](#-getting-started) ·
[Tests](#-testing) ·
[Roadmap](#-remaining-roadmap)

</div>

---

## 📖 Overview

**TaskFlow** is a full-stack Django portfolio project for collaborative task and project management.

The project was built primarily to demonstrate backend engineering and application architecture skills rather than to operate as a commercial production service.

Its main focus areas are:

* Django application architecture
* Service and selector layers
* Role-based authorization
* Resource hierarchy validation
* Transaction-safe mutations
* Database constraints
* Drag-and-drop ordering
* Notification workflows
* Email verification
* Redis-backed coordination
* Automated testing
* Responsive Persian RTL interfaces
* Modern frontend interaction and motion

TaskFlow follows the hierarchy:

```text
Workspace
└── Board
    └── Column
        └── Task
            ├── Comments
            └── Activity history
```

The application is server-rendered with Django Templates while JavaScript is used selectively for richer interactions such as drag-and-drop, responsive navigation, notifications, Three.js visuals, and UI motion.

---

## 🎯 Project Purpose

TaskFlow is a **portfolio and learning project**.

It is intended to demonstrate how I approach:

* Domain modeling
* Business rules
* Database integrity
* Permissions
* Transactions
* Reusable application services
* Query organization
* Testing
* Frontend/backend integration
* Maintainable Django project structure

The repository also contains environment-specific deployment configuration for PostgreSQL, Redis, SMTP, CSP, Gunicorn, and HTTPS-related Django settings.

Those configurations exist to demonstrate deployment awareness and environment separation.

They should not be interpreted as a claim that TaskFlow is currently operated as a production SaaS.

---

# ✨ Features

## 🔐 Authentication & Accounts

TaskFlow includes a complete custom authentication flow.

### Account lifecycle

* Custom Django user model
* Registration
* Normalized email addresses
* Case-insensitive email uniqueness
* Inactive account creation
* Email verification before activation
* Secure activation tokens
* Activation-link validation
* Activation resend flow
* Resend cooldown
* Login
* Logout
* Password reset by email
* Authenticated password change
* Session preservation after password change

### Activation protection

Activation email resends use an atomic cache lock.

Example cache key:

```text
user:<user-id>:verification:resend-lock
```

This prevents duplicate concurrent resend requests during the cooldown period.

---

## 👤 Profile Management

Users can manage their personal profile.

Supported functionality includes:

* First name
* Last name
* Username
* Biography
* Avatar upload
* Avatar replacement
* Image-type validation
* File-size validation
* Randomized stored filenames
* User-specific avatar paths

Supported image formats include:

```text
JPG
JPEG
PNG
WEBP
GIF
```

---

# 🏢 Workspaces

Workspaces are the highest-level collaborative resource.

Users can:

* Create workspaces
* View accessible workspaces
* Search workspaces
* Update workspaces
* Archive workspaces
* Restore archived workspaces
* Permanently remove eligible archived resources
* View workspace members
* Invite users
* Accept invitations
* Reject invitations
* Manage member roles
* Remove eligible members

Invitation handling includes:

* Expiration
* Unique tokens
* Email ownership checks
* Duplicate invitation protection
* Transactional acceptance
* Transactional rejection
* Database row locking

---

# 🛡️ Role-Based Access Control

TaskFlow currently supports four workspace roles:

| Role       | Capabilities                                                         |
| ---------- | -------------------------------------------------------------------- |
| **Owner**  | Full workspace control and ownership-level administration            |
| **Admin**  | Workspace administration and member management within defined limits |
| **Member** | Collaborative write access to project content                        |
| **Viewer** | Read-only access                                                     |

Examples of enforced rules:

* The Owner cannot be removed using the normal membership removal workflow.
* Only the Owner can grant Admin privileges.
* Admins cannot modify or remove other Admins.
* Members cannot manage workspace membership.
* Viewers cannot mutate collaborative resources.
* Archived resources are excluded from normal active-resource flows.
* Invitations cannot grant ownership.
* Backend permission checks remain authoritative even when UI controls are hidden.

Permissions are enforced at the backend rather than relying only on presentation logic.

---

# 🗂️ Boards

Each workspace can contain multiple boards.

Board functionality includes:

* Board creation
* Board editing
* Board listing
* Board detail pages
* Archive
* Restore
* Permanent deletion of eligible archived boards
* Board-level permission enforcement
* Active/archived scoping
* Progress summaries
* Timestamp propagation from child mutations

---

# 🧱 Columns

Boards contain ordered columns.

Column functionality includes:

* Create
* Edit
* Archive
* Restore
* Permanent deletion
* Ordered positioning
* Previous/next movement
* Drag-and-drop reordering
* Server-side ordering validation
* Position normalization
* Transactional updates

Active column positions are kept contiguous.

Reordering preserves the database uniqueness constraint by temporarily staging positions before the final order is written.

---

# ✅ Tasks

Tasks form the main workflow unit of TaskFlow.

A task supports:

* Title
* Description
* Priority
* Status
* Assignee
* Creator
* Due date
* Column position
* Archive state
* Archive timestamp

## Task priority

Available priorities:

```text
Low
Medium
High
Urgent
```

## Task status

Available statuses:

```text
To do
In progress
Blocked
Done
Canceled
```

## Assignment rules

Tasks can only be assigned to users who are eligible members of the related workspace.

Assignment validation is enforced in backend domain logic rather than only through forms.

---

# ↕️ Task Ordering & Movement

Tasks support rich reordering behavior.

Users with write access can:

* Reorder a task inside the same column
* Move a task between columns
* Use drag-and-drop
* Use server-rendered fallback movement controls

The ordering implementation includes:

* Transactional row locking
* Temporary position staging
* Position normalization
* Optimistic frontend updates
* Backend response reconciliation
* Rollback on request failure
* CSRF protection
* Permission-aware interaction
* Viewer read-only mode

Column and Task drag operations are coordinated so overlapping writes do not conflict.

---

# 💬 Task Comments

Tasks support collaborative comments.

Features include:

* Comment creation
* Author editing
* Soft deletion
* Administrative moderation
* Deleted-comment tracking
* Comment timestamps
* Comment author retention behavior

Comment deletion stores:

* Delete state
* Deletion time
* Deleting user

Database constraints ensure the deletion state remains internally consistent.

---

# 🕒 Activity History

Important task mutations are recorded as structured activity events.

Tracked actions include:

* Task creation
* General updates
* Status changes
* Assignee changes
* Movement between columns
* Reordering
* Comment creation
* Comment updates
* Comment deletion
* Archive
* Restore

Activity entries contain structured JSON metadata where appropriate.

This provides a reusable audit-style event history without introducing implicit Django signals.

---

# 🔔 Notifications

TaskFlow includes an in-app notification domain.

Supported notification events include:

* Task assignment
* Task reassignment
* Task status changes
* New task comments
* Workspace invitations
* Workspace role changes
* Workspace membership removal

Notification functionality includes:

* Per-user inbox
* Read/unread state
* Unread counts
* Header badge
* Header dropdown
* Mark one as read
* Mark all as read
* Related-object navigation
* Safe redirect validation
* User-scoped access

Self-notifications are avoided where appropriate.

---

# 📊 Dashboard

The dashboard is built from real application data rather than placeholder statistics.

It includes:

* Accessible workspace count
* Active board count
* Assigned task count
* Completed task count
* Overdue tasks
* Upcoming deadlines
* Personal progress
* Workspace progress
* Board progress
* Recently assigned tasks
* Recent task activity
* Recent notifications

Dashboard queries are scoped to resources the authenticated user is actually allowed to access.

Archived workspace, board, column, and task hierarchies are excluded from normal active metrics.

---

# 🎨 UI / UX

TaskFlow uses a Persian-first interface designed for RTL layouts.

Frontend highlights include:

* Full RTL layout
* Persian interface terminology
* Responsive mobile-first design
* Light and dark themes
* Glassmorphism-inspired visual system
* Animated backgrounds
* Three.js visual effects
* GSAP motion
* Responsive desktop sidebar
* Mobile bottom navigation
* Scrollable mobile drawer
* Accessible focus handling
* Reduced-motion support
* Accessible notification interactions
* Touch-friendly controls
* Responsive board scrolling

Interactive visual effects are treated as enhancements rather than requirements for basic application functionality.

---

# 🧠 Engineering Highlights

TaskFlow intentionally contains several patterns that go beyond basic CRUD.

## Service layer

Mutation-heavy business logic is moved away from HTTP views and into reusable services.

Examples include:

```text
Workspace lifecycle
Workspace invitations
Membership management
Board lifecycle
Column lifecycle
Column reordering
Task lifecycle
Task reordering
Task comments
Task activity
Notification delivery
Account activation
```

Views remain primarily responsible for:

* HTTP input
* Forms
* Messages
* Redirects
* JSON parsing
* Response construction

---

## Selector layer

Reusable ORM-heavy read operations are organized into selectors.

This keeps complex query composition out of templates and reduces duplication between views and metrics.

---

## Transaction safety

Important mutations use:

```python
transaction.atomic()
```

and, where concurrent access matters:

```python
select_for_update()
```

This is used in workflows such as:

* Invitation processing
* Account activation
* Column reordering
* Task reordering
* Lifecycle mutations

---

## Database constraints

The project uses database constraints for important invariants such as:

* Active task position uniqueness
* Active column position uniqueness
* Archive-state consistency
* Comment deletion consistency
* Notification read-state consistency

Application validation and database constraints are used together where appropriate.

---

## Explicit domain events

Task activity and notifications are triggered through explicit service integration.

The project intentionally avoids relying on a large implicit signal architecture for business workflows.

This keeps side effects easier to trace and test.

---

# 🚀 Environment Architecture

TaskFlow separates Django settings into dedicated environments:

```text
config/settings/
├── base.py
├── development.py
├── test.py
└── production.py
```

## Development

Development uses:

* SQLite
* Console email backend
* Debug Toolbar
* Optional Redis
* Optional RedisBoard

Redis is not required for basic local development.

## Test

The isolated test environment uses:

* In-memory SQLite
* Local-memory cache
* In-memory email backend
* Separate test media storage

The test suite does not require external Redis, PostgreSQL, or SMTP services.

## Deployment profile

The repository also contains an optional deployment-oriented settings profile demonstrating integration with:

* PostgreSQL
* Redis
* SMTP
* Gunicorn
* Secure cookies
* HTTPS settings
* HSTS
* Content Security Policy
* Manifest static files
* Structured logging

This configuration exists as part of the engineering portfolio and deployment-learning scope.

TaskFlow is not presented as a currently hosted production service.

---

# 💾 Caching

Django's cache abstraction is used in the project.

Current concrete cache usage includes the account activation resend lock.

Development can optionally use Redis.

The deployment-oriented configuration uses Redis as a shared cache backend.

Generalized application caching for dashboard metrics and selector results is intentionally still limited and remains an area for future improvement.

---

# 📧 Email

TaskFlow currently generates email for workflows including:

* Account activation
* Activation resend
* Password reset
* Workspace invitations

Email templates support both text and HTML where implemented.

## Development

Development uses Django's console email backend.

Emails and links appear directly in the terminal.

## Tests

Tests use Django's in-memory email backend.

## Deployment profile

The deployment-oriented settings support SMTP configuration through environment variables.

Email delivery is currently synchronous.

The project does not yet implement:

* Background email queues
* Celery workers
* Retry scheduling
* Delivery analytics
* Bounce processing
* Provider-specific webhooks

Those features are outside the current portfolio scope unless added later.

---

# 🧰 Technology Stack

## Backend

| Technology               | Purpose                              |
| ------------------------ | ------------------------------------ |
| **Python 3.14+**         | Primary programming language         |
| **Django 6**             | Web framework                        |
| **SQLite**               | Local development and tests          |
| **PostgreSQL / Psycopg** | Deployment-oriented database support |
| **Redis**                | Shared cache support                 |
| **django-redis**         | Django cache backend integration     |
| **hiredis**              | Redis protocol parsing               |
| **Pillow**               | Avatar and image processing          |
| **python-decouple**      | Environment configuration            |
| **Gunicorn**             | WSGI deployment configuration        |

## Frontend

| Technology             | Purpose                       |
| ---------------------- | ----------------------------- |
| **Django Templates**   | Server-rendered frontend      |
| **HTML5**              | Semantic structure            |
| **CSS3**               | Responsive RTL interface      |
| **Vanilla JavaScript** | Client-side interaction       |
| **Three.js**           | Animated 3D background        |
| **GSAP**               | Interface motion              |
| **SortableJS**         | Task and column drag-and-drop |

## Development

| Technology               | Purpose                   |
| ------------------------ | ------------------------- |
| **Poetry**               | Dependency management     |
| **Django TestCase**      | Automated tests           |
| **Django Debug Toolbar** | Development diagnostics   |
| **RedisBoard**           | Optional Redis inspection |
| **IPython**              | Development shell         |

---

# 🗂️ Architecture

```text
taskflow-django-application/
│
├── apps/
│   ├── accounts/
│   ├── boards/
│   ├── columns/
│   ├── core/
│   ├── dashboard/
│   ├── notifications/
│   ├── tasks/
│   └── workspaces/
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── test.py
│   │   └── production.py
│   │
│   ├── asgi.py
│   ├── urls.py
│   └── wsgi.py
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/
│
├── manage.py
├── gunicorn.conf.py
├── pyproject.toml
├── poetry.lock
├── .env.example
├── .env.production.example
└── README.md
```

## Application responsibilities

| Application     | Responsibility                                             |
| --------------- | ---------------------------------------------------------- |
| `accounts`      | Users, registration, authentication and email verification |
| `workspaces`    | Workspaces, memberships, roles and invitations             |
| `boards`        | Board lifecycle and board access                           |
| `columns`       | Column lifecycle and ordering                              |
| `tasks`         | Tasks, comments, activities and reordering                 |
| `notifications` | In-app notification persistence and read state             |
| `dashboard`     | User dashboard, metrics and profile                        |
| `core`          | Shared models, permissions and utilities                   |

---

# 🚀 Getting Started

## Requirements

You need:

* Python 3.14+
* Poetry
* Git

Redis is optional for normal local development.

---

## 1. Clone the project

```bash
git clone https://github.com/funlifew/taskflow-django-application.git
cd taskflow-django-application
```

---

## 2. Install dependencies

```bash
poetry install
```

---

## 3. Configure the development environment

Copy the example file:

```bash
cp .env.example .env
```

Windows CMD:

```cmd
copy .env.example .env
```

Basic local development works without Redis.

Example configuration:

```env
DJANGO_SETTINGS_MODULE=config.settings.development

DEV_USE_REDIS=False

REDIS_URL=redis://127.0.0.1:6379/1

ENABLE_REDISBOARD=False
```

---

## 4. Apply migrations

```bash
poetry run python manage.py migrate
```

---

## 5. Create a superuser

```bash
poetry run python manage.py createsuperuser
```

---

## 6. Start the development server

```bash
poetry run python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Django Admin:

```text
http://127.0.0.1:8000/admin/
```

---

# ⚡ Optional Redis Development

To test Redis-backed functionality locally:

```env
DEV_USE_REDIS=True
REDIS_URL=redis://127.0.0.1:6379/1
```

Then run Redis locally or with Docker:

```bash
docker run \
  --name taskflow-redis \
  -p 6379:6379 \
  -d redis:alpine
```

Redis is not required when `DEV_USE_REDIS=False`.

---

# 📧 Development Email Behavior

Development uses Django's console backend.

For example, account activation or password-reset emails are printed into the terminal:

```text
Subject: فعالسازی حساب TaskFlow

http://127.0.0.1:8000/...
```

No external email provider is required for development.

---

# 🧪 Testing

Use the isolated test settings:

```bash
poetry run python manage.py test \
  --settings=config.settings.test \
  -v 2
```

Run a specific application:

```bash
poetry run python manage.py test \
  apps.tasks.tests \
  --settings=config.settings.test \
  -v 2
```

Run Django system checks:

```bash
poetry run python manage.py check \
  --settings=config.settings.development
```

Check for missing migrations:

```bash
poetry run python manage.py makemigrations \
  --check \
  --dry-run \
  --settings=config.settings.test
```

The test environment is isolated from external infrastructure so the project can be tested without PostgreSQL, Redis, or SMTP.

---

# 📌 Current Status

The core portfolio application is largely implemented.

## Completed

* [x] Custom user model
* [x] Registration
* [x] Email verification
* [x] Password reset
* [x] Profile management
* [x] Avatar uploads
* [x] Workspace CRUD
* [x] Workspace memberships
* [x] Workspace roles
* [x] Workspace invitations
* [x] Board CRUD
* [x] Board archive/restore
* [x] Column CRUD
* [x] Column ordering
* [x] Column drag-and-drop
* [x] Task CRUD
* [x] Task assignment
* [x] Task priorities
* [x] Task statuses
* [x] Due dates
* [x] Task archive/restore
* [x] Task movement
* [x] Task drag-and-drop
* [x] Task comments
* [x] Task activity history
* [x] In-app notifications
* [x] Notification header integration
* [x] Dashboard metrics
* [x] Workspace progress
* [x] Board progress
* [x] Persian RTL interface
* [x] Mobile-first UI
* [x] Three.js background
* [x] GSAP motion
* [x] Dark/light themes
* [x] Environment-specific Django settings
* [x] PostgreSQL configuration
* [x] Redis deployment configuration
* [x] SMTP configuration
* [x] CSP configuration
* [x] Automated regression tests

---

# 🗺️ Remaining Roadmap

The core functionality is complete enough to serve as a backend portfolio project.

Remaining work is primarily focused on refinement, engineering depth, testing, and presentation.

## Phase 1 — Email Reliability

* [ ] Audit every email-producing workflow
* [ ] Centralize shared email construction where useful
* [ ] Add stronger email-delivery tests
* [ ] Improve failure handling
* [ ] Improve logging around delivery failures
* [ ] Review activation, reset and invitation templates
* [ ] Consider a provider abstraction if it improves the portfolio

Background queues are optional and should only be added if they meaningfully demonstrate architecture rather than adding unnecessary complexity.

---

## Phase 2 — Redis Application Caching

* [ ] Define a cache-key convention
* [ ] Identify expensive dashboard queries
* [ ] Cache selected user dashboard summaries
* [ ] Cache selected workspace/board aggregates
* [ ] Add explicit invalidation
* [ ] Test stale-cache scenarios
* [ ] Test cache failure behavior
* [ ] Prevent cache stampedes where relevant

Avoid full-page caching for user-specific authenticated pages.

---

## Phase 3 — Permission & Hierarchy Audit

Perform a dedicated authorization audit covering:

```text
Anonymous
Outsider
Viewer
Member
Admin
Owner
```

against:

```text
Workspace
Board
Column
Task
Comment
Notification
Invitation
Archive
Restore
Reordering
```

Test resource-ID tampering across unrelated hierarchies.

Example:

```text
Workspace A
└── Board A
    └── Column A

Workspace B
└── Board B
    └── Column B
```

Requests mixing IDs from different hierarchies must fail safely.

---

## Phase 4 — Archive / Restore Integrity

* [ ] Audit workspace archive behavior
* [ ] Audit board archive behavior
* [ ] Audit column archive behavior
* [ ] Audit task archive behavior
* [ ] Verify child-resource visibility
* [ ] Verify restore ordering
* [ ] Verify permanent-deletion restrictions
* [ ] Test nested archived-resource edge cases

---

## Phase 5 — Engineering Quality

* [ ] Add GitHub Actions
* [ ] Run the full test suite in CI
* [ ] Add coverage measurement
* [ ] Publish a coverage badge
* [ ] Add linting/formatting checks
* [ ] Add security-oriented test cases
* [ ] Remove remaining dead code
* [ ] Review database indexes
* [ ] Run query-count checks on expensive views

---

## Phase 6 — Portfolio Presentation

* [ ] Add application screenshots
* [ ] Add a short demo GIF/video
* [ ] Add an architecture diagram
* [ ] Add a permissions matrix
* [ ] Add a data-model diagram
* [ ] Improve GitHub repository description
* [ ] Add repository topics
* [ ] Add a proper LICENSE file
* [ ] Add example demo data or seed tooling
* [ ] Document the most interesting engineering decisions

---

## Phase 7 — Final Stabilization

* [ ] Full regression pass
* [ ] Mobile QA
* [ ] RTL QA
* [ ] Accessibility pass
* [ ] Dark/light theme pass
* [ ] Drag-and-drop QA
* [ ] Email-flow QA
* [ ] Cache behavior QA
* [ ] Permission audit
* [ ] Archive/restore audit
* [ ] Final README review

At that point, the project can be considered complete as a portfolio project.

---

# 🚫 Intentional Non-Goals

TaskFlow does not need to become a large commercial SaaS to fulfill its portfolio purpose.

The following are intentionally optional:

* Kubernetes
* Microservices
* Event streaming
* Kafka
* Complex background-worker infrastructure
* Real-time collaborative editing
* WebSockets everywhere
* Multi-region deployment
* Full observability platforms
* Large-scale distributed caching
* Premature service decomposition

Additional infrastructure should only be introduced when it demonstrates a meaningful engineering decision.

---

# 📄 License

The project metadata declares the project as MIT licensed.

A standalone `LICENSE` file should still be added to the repository.

---

# 👨‍💻 Author

<div align="center">

### Mehdi Radfar

Backend Developer focused on **Python, Django and FastAPI**.

</div>

---

<div align="center">

### ⭐ TaskFlow

Built as a backend engineering portfolio project with an emphasis on architecture,
permissions, transactional workflows, testing, and thoughtful user experience.

</div>
