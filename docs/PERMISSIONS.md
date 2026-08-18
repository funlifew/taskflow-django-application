# TaskFlow Permission Matrix

TaskFlow authorization is based on Workspace membership roles combined with nested-resource scoping.

Roles:

| Role | Description |
|---|---|
| Owner | Workspace owner with full administrative control |
| Admin | Administrative collaborator |
| Member | Collaborative writer |
| Viewer | Read-only collaborator |
| Outsider | Authenticated user without Workspace membership |

---

## Workspace

| Operation | Owner | Admin | Member | Viewer | Outsider |
|---|:---:|:---:|:---:|:---:|:---:|
| View Workspace | ✅ | ✅ | ✅ | ✅ | ❌ |
| View members | ✅ | ✅ | ✅ | ✅ | ❌ |
| Edit Workspace | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete Workspace | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite members | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage member roles | ✅ | Limited | ❌ | ❌ | ❌ |
| Remove members | ✅ | Limited | ❌ | ❌ | ❌ |

Admin limitations include:

- Cannot modify the Owner.
- Cannot remove the Owner.
- Cannot modify another Admin.
- Cannot remove another Admin.
- Cannot promote an existing member to Admin.

The Owner role cannot be assigned through the normal membership role-change workflow.

---

## Boards, Columns and Tasks

| Operation | Owner | Admin | Member | Viewer | Outsider |
|---|:---:|:---:|:---:|:---:|:---:|
| Read | ✅ | ✅ | ✅ | ✅ | ❌ |
| Create | ✅ | ✅ | ✅ | ❌ | ❌ |
| Update | ✅ | ✅ | ✅ | ❌ | ❌ |
| Archive | ✅ | ✅ | ✅ | ❌ | ❌ |
| Restore | ✅ | ✅ | ✅ | ❌ | ❌ |
| Reorder | ✅ | ✅ | ✅ | ❌ | ❌ |
| Permanent delete of eligible archived resource | ✅ | ✅ | ❌ | ❌ | ❌ |

Collaborative write access is shared by:

```text
Owner
Admin
Member