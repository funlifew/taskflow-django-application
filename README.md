<div align="center">

# 🚀 TaskFlow

### A modern, secure and scalable task management platform built with Django

<p>
  TaskFlow is a Persian-first collaborative task management application designed around
  workspaces, role-based permissions and secure team collaboration.
</p>

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge\&logo=python\&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge\&logo=django\&logoColor=white)](https://www.djangoproject.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge\&logo=redis\&logoColor=white)](https://redis.io/)
[![Poetry](https://img.shields.io/badge/Poetry-Dependency_Manager-60A5FA?style=for-the-badge\&logo=poetry\&logoColor=white)](https://python-poetry.org/)
[![Tests](https://img.shields.io/badge/Tests-Automated-success?style=for-the-badge\&logo=pytest\&logoColor=white)](#-testing)
[![Status](https://img.shields.io/badge/Status-Active_Development-orange?style=for-the-badge)](#-project-status)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](#-license)

<br>

[Features](#-features) ·
[Architecture](#-project-architecture) ·
[Installation](#-getting-started) ·
[Testing](#-testing) ·
[Roadmap](#-roadmap)

</div>

---

## 📖 About TaskFlow

**TaskFlow** is a server-rendered task management application built with Django.

The project is being developed as a production-oriented backend portfolio project, with an emphasis on:

* Clean application architecture
* Secure authentication flows
* Role-based access control
* Transaction-safe business logic
* Automated testing
* Reusable Django components
* Responsive Persian RTL user interface

TaskFlow is not just a collection of CRUD pages. Its architecture is designed to support a complete collaborative workflow:

```text
Workspace
└── Board
    └── Column
        └── Task
```

The authentication, dashboard and workspace foundations are already implemented. Boards, columns and tasks are the next major development phases.

---

## ✨ Features

### 🔐 Authentication and Accounts

* Custom Django user model
* User registration
* Case-insensitive unique email addresses
* Automatic email normalization
* Inactive accounts before email verification
* Secure account activation tokens
* Email verification flow
* Activation email resend
* Redis-backed resend cooldown
* Protection against account enumeration
* Login and logout
* Password reset by email
* Authenticated password change
* Session preservation after password change

### 👤 User Profile

* Personal profile page
* First name and last name editing
* Username editing
* Case-insensitive username validation
* Personal biography
* Profile avatar upload
* Supported avatar formats:

  * JPG
  * JPEG
  * PNG
  * WEBP
  * GIF
* Maximum avatar size validation
* Secure randomized avatar filenames
* User-specific avatar directories

### 🏢 Workspace Management

* Create workspaces
* View accessible workspaces
* Search workspaces
* Update workspaces
* Delete workspaces
* Archive-aware access control
* Workspace member listing
* Workspace statistics
* Membership roles
* Role-based permission checks
* Workspace invitation system
* Email invitation delivery
* Invitation expiration
* Invitation acceptance
* Invitation rejection
* Duplicate invitation protection
* Transaction-safe invitation processing
* Concurrent request protection using database row locks

### 🛡️ Role-Based Access Control

TaskFlow currently supports four workspace roles:

| Role       | Capabilities                                                                     |
| ---------- | -------------------------------------------------------------------------------- |
| **Owner**  | Full workspace control, member management, role management, editing and deletion |
| **Admin**  | Invite users and manage members or viewers                                       |
| **Member** | Access workspace content and member information                                  |
| **Viewer** | Read-only workspace access                                                       |

Important permission rules include:

* A workspace owner cannot be removed through the member removal flow.
* Only the owner can promote another user to Admin.
* Admins cannot update or remove other Admins.
* Members and Viewers cannot invite or manage users.
* Archived workspaces cannot be accessed through normal workspace routes.
* Workspace invitations cannot grant the Owner role.

### 🎨 User Interface

* Persian-first interface
* RTL layout
* Responsive design
* Reusable Django templates
* Custom form components
* Styled validation messages
* Role badges
* User avatars
* Workspace cards
* Authentication pages
* Profile pages
* Member management pages
* Invitation pages
* Custom error pages

### 🧪 Automated Tests

The project includes automated tests for:

* User model behavior
* Email normalization
* Database constraints
* Registration forms
* Profile forms
* Authentication tokens
* Activation email services
* Redis cooldown behavior
* Registration flow
* Account activation
* Login and logout
* Password reset
* Password change
* Dashboard access
* Profile updates
* Avatar validation
* Workspace models
* Workspace forms
* Workspace services
* Workspace invitations
* Workspace permissions
* Workspace views
* Member role management

---

## 🔒 Security and Reliability

TaskFlow applies several defensive patterns throughout the application.

### Authentication security

* Users remain inactive before email verification.
* Activation tokens become invalid after account activation.
* Activation tokens depend on the user's email and verification state.
* Email addresses are unique regardless of letter casing.
* Resend responses do not reveal whether an account exists.

### Rate limiting

Activation emails use an atomic Redis cache lock:

```text
user:<user-id>:verification:resend-lock
```

This prevents repeated or concurrent activation-email requests during the cooldown period.

### Transaction safety

Important business operations are executed inside database transactions.

Invitation acceptance and rejection use:

```python
transaction.atomic()
select_for_update()
```

This prevents two simultaneous requests from processing the same invitation incorrectly.

### Permission safety

Permissions are enforced in backend mixins and querysets rather than only being hidden in the user interface.

Unauthorized users receive the appropriate:

* Login redirect
* `403 Forbidden`
* `404 Not Found`

response depending on the operation.

---

## 🧰 Technology Stack

### Backend

| Technology      | Usage                               |
| --------------- | ----------------------------------- |
| Python 3.14+    | Main programming language           |
| Django 6        | Web framework                       |
| SQLite          | Current development database        |
| Redis           | Cache and activation-email cooldown |
| django-redis    | Django cache integration            |
| hiredis         | Faster Redis protocol parsing       |
| Pillow          | Avatar and image handling           |
| python-decouple | Environment variable management     |

### Development

| Technology           | Usage                                         |
| -------------------- | --------------------------------------------- |
| Poetry               | Dependency and virtual environment management |
| Django TestCase      | Automated application tests                   |
| Django Debug Toolbar | Development diagnostics                       |
| Redisboard           | Redis monitoring through Django Admin         |
| IPython              | Improved interactive shell                    |

### Frontend

* Django Templates
* HTML5
* CSS3
* Vanilla JavaScript
* Responsive RTL design

---

## 🗂️ Project Architecture

```text
taskflow-django-application/
│
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   ├── tokens.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── dashboard/
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── workspaces/
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── boards/
│   ├── tasks/
│   ├── notifications/
│   └── core/
│       ├── models.py
│       ├── mixins.py
│       └── cache_keys.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── static/
├── templates/
├── media/
├── manage.py
├── pyproject.toml
├── poetry.lock
├── .env.example
└── README.md
```

### Application responsibilities

| Application     | Responsibility                                                  |
| --------------- | --------------------------------------------------------------- |
| `accounts`      | User model, registration, authentication and email verification |
| `dashboard`     | Dashboard and user profile management                           |
| `workspaces`    | Workspace CRUD, memberships, roles and invitations              |
| `boards`        | Board and column management — planned                           |
| `tasks`         | Task lifecycle and assignment — planned                         |
| `notifications` | User notifications — planned                                    |
| `core`          | Shared models, permission mixins and utility functions          |

---

## 🚀 Getting Started

### Prerequisites

Before installing the project, make sure you have:

* Python 3.14 or newer
* Poetry
* Redis
* Git

### 1. Clone the repository

```bash
git clone https://github.com/funlifew/taskflow-django-application.git
cd taskflow-django-application
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Configure environment variables

Copy the provided example:

```bash
cp .env.example .env
```

On Windows Command Prompt:

```cmd
copy .env.example .env
```

Default development configuration:

```env
SECRET_KEY=replace-this-with-a-secure-secret-key
DEBUG=True

REDIS_URL=redis://localhost:6379/1
```

Generate a secure Django secret key:

```bash
poetry run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Paste the generated value into `.env`.

### 4. Start Redis

Using an installed Redis server:

```bash
redis-server
```

Or using Docker:

```bash
docker run --name taskflow-redis \
  -p 6379:6379 \
  -d redis:alpine
```

### 5. Apply database migrations

```bash
poetry run python manage.py migrate
```

### 6. Create an administrator

```bash
poetry run python manage.py createsuperuser
```

### 7. Run the development server

```bash
poetry run python manage.py runserver
```

Open the application at:

```text
http://127.0.0.1:8000/
```

Django Admin is available at:

```text
http://127.0.0.1:8000/admin/
```

---

## 📧 Development Email Behavior

The development configuration uses Django's console email backend.

Activation links, password-reset links and workspace invitations are printed directly in the terminal running the Django server.

Example:

```text
Content-Type: text/plain
Subject: فعالسازی حساب TaskFlow

http://127.0.0.1:8000/activate/<uid>/<token>/
```

A production deployment should replace the console backend with a real email provider.

---

## 🧪 Testing

Run all project tests:

```bash
poetry run python manage.py test -v 2
```

Run only Account and Authentication tests:

```bash
poetry run python manage.py test apps.accounts.tests -v 2
```

Run Dashboard tests:

```bash
poetry run python manage.py test apps.dashboard.tests -v 2
```

Run Workspace tests:

```bash
poetry run python manage.py test apps.workspaces.tests -v 2
```

Run all currently implemented application tests:

```bash
poetry run python manage.py test \
  apps.accounts.tests \
  apps.dashboard.tests \
  apps.workspaces.tests \
  -v 2
```

Run Django's system checks:

```bash
poetry run python manage.py check
```

### Test isolation

Tests override external infrastructure where appropriate.

For example, account tests use Django's in-memory cache instead of requiring a running Redis server. This keeps the test suite:

* Fast
* Deterministic
* Independent
* Easy to run in CI environments

---

## 📌 Project Status

TaskFlow is currently under active development.

### Completed foundations

* [x] Custom user model
* [x] Registration system
* [x] Email verification
* [x] Activation resend cooldown
* [x] Login and logout
* [x] Password reset
* [x] Password change
* [x] Dashboard
* [x] Profile management
* [x] Avatar upload and validation
* [x] Workspace CRUD
* [x] Workspace memberships
* [x] Role-based permissions
* [x] Workspace invitations
* [x] Invitation expiration
* [x] Automated tests for implemented applications
* [x] Responsive Persian RTL interface

---

## 🗺️ Roadmap

### Phase 1 — Foundation

* [x] Accounts and authentication
* [x] User profiles
* [x] Workspace management
* [x] Team memberships
* [x] Workspace invitations
* [x] Permission system
* [x] Automated tests

### Phase 2 — Boards and Columns

* [ ] Board model
* [ ] Board CRUD
* [ ] Board permissions
* [ ] Column model
* [ ] Column ordering
* [ ] Archive functionality
* [ ] Board and column tests

### Phase 3 — Tasks

* [ ] Task model
* [ ] Task CRUD
* [ ] Task assignment
* [ ] Due dates
* [ ] Priorities
* [ ] Task status
* [ ] Task movement between columns
* [ ] Task ordering
* [ ] Task tests

### Phase 4 — Collaboration

* [ ] Labels
* [ ] Checklists
* [ ] Comments
* [ ] Activity history
* [ ] Mentions
* [ ] Notifications

### Phase 5 — Production Readiness

* [ ] PostgreSQL
* [ ] Docker and Docker Compose
* [ ] GitHub Actions CI
* [ ] Test coverage report
* [ ] Structured logging
* [ ] Production email provider
* [ ] Static file production setup
* [ ] Deployment documentation
* [ ] Live deployment

---

## 🤝 Contributing

Contributions, suggestions and bug reports are welcome.

### Development workflow

1. Fork the repository.
2. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

3. Make your changes.
4. Add or update tests.
5. Run the test suite:

```bash
poetry run python manage.py test
```

6. Commit your changes:

```bash
git commit -m "Add your feature"
```

7. Push the branch:

```bash
git push origin feature/your-feature-name
```

8. Open a Pull Request.

Please keep changes focused and include tests for new business logic.

---

## 🐛 Reporting Issues

When reporting a bug, include:

* A clear description of the problem
* Steps to reproduce it
* Expected behavior
* Actual behavior
* Python version
* Django version
* Operating system
* Relevant logs or screenshots

Issues can be submitted through the repository's GitHub Issues section.

---

## 📄 License

The project is distributed under the **MIT License**.

A standalone `LICENSE` file should be added to the repository before the first public release.

---

## 👨‍💻 Author

<div align="center">

### Mehdi Radfar

Backend Developer focused on Python, Django and FastAPI.

[![GitHub](https://img.shields.io/badge/GitHub-funlifew-181717?style=for-the-badge\&logo=github)](https://github.com/funlifew)

</div>

---

<div align="center">

### ⭐ Support the Project

If you find TaskFlow useful or interesting, consider giving the repository a star.

Made with Python, Django and a lot of attention to clean backend architecture.

</div>
