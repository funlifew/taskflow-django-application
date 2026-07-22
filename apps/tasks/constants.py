from apps.workspaces.models import WorkspaceMembership


TASK_ASSIGNABLE_ROLES = (
    WorkspaceMembership.Role.OWNER,
    WorkspaceMembership.Role.ADMIN,
    WorkspaceMembership.Role.MEMBER,
)