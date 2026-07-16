from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.workspaces.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)


User = get_user_model()


class WorkspaceTestBase(TestCase):
    password = "StrongPass123!"

    @classmethod
    def setUpTestData(cls):
        cls.owner = cls.create_user(
            username="owner",
            email="owner@example.com",
        )
        cls.admin = cls.create_user(
            username="admin",
            email="admin@example.com",
        )
        cls.member = cls.create_user(
            username="member",
            email="member@example.com",
        )
        cls.viewer = cls.create_user(
            username="viewer",
            email="viewer@example.com",
        )
        cls.outsider = cls.create_user(
            username="outsider",
            email="outsider@example.com",
        )
        cls.invited_user = cls.create_user(
            username="invited",
            email="invited@example.com",
        )

        cls.workspace = Workspace.objects.create(
            name="TaskFlow",
            description="Main test workspace",
            owner=cls.owner,
        )

        cls.owner_membership = (
            WorkspaceMembership.objects.create(
                workspace=cls.workspace,
                user=cls.owner,
                role=WorkspaceMembership.Role.OWNER,
            )
        )

        cls.admin_membership = (
            WorkspaceMembership.objects.create(
                workspace=cls.workspace,
                user=cls.admin,
                role=WorkspaceMembership.Role.ADMIN,
            )
        )

        cls.member_membership = (
            WorkspaceMembership.objects.create(
                workspace=cls.workspace,
                user=cls.member,
                role=WorkspaceMembership.Role.MEMBER,
            )
        )

        cls.viewer_membership = (
            WorkspaceMembership.objects.create(
                workspace=cls.workspace,
                user=cls.viewer,
                role=WorkspaceMembership.Role.VIEWER,
            )
        )

    @classmethod
    def create_user(
        cls,
        *,
        username,
        email,
    ):
        return User.objects.create_user(
            username=username,
            email=email,
            password=cls.password,
            first_name=username.title(),
            last_name="Tester",
            email_verified=True,
        )

    def create_invitation(
        self,
        *,
        workspace=None,
        email=None,
        invited_by=None,
        role=WorkspaceMembership.Role.MEMBER,
        status=WorkspaceInvitation.Status.PENDING,
        expires_at=None,
    ):
        return WorkspaceInvitation.objects.create(
            workspace=workspace or self.workspace,
            invited_by=invited_by or self.owner,
            email=email or self.invited_user.email,
            role=role,
            status=status,
            expires_at=expires_at or (
                timezone.now() + timedelta(days=3)
            ),
        )