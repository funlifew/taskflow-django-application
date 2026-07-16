from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.accounts.models import (
    create_random_avatar,
    user_directory_path,
)

from apps.accounts.tests.base import AccountsTestBase


User = get_user_model()


class UserModelTests(AccountsTestBase):
    def test_user_string_representation(self):
        self.assertEqual(
            str(self.active_user),
            self.active_user.username,
        )

    def test_email_is_normalized_when_user_is_saved(self):
        user = User.objects.create_user(
            username="normalized",
            email="  NORMALIZED@EXAMPLE.COM  ",
            password=self.password,
            first_name="Normalized",
            last_name="User",
        )

        self.assertEqual(
            user.email,
            "normalized@example.com",
        )

    def test_email_is_case_insensitively_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="duplicate-email",
                    email="SHELLY@EXAMPLE.COM",
                    password=self.password,
                    first_name="Duplicate",
                    last_name="User",
                )

    def test_default_email_verified_is_false(self):
        user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password=self.password,
            first_name="Unverified",
            last_name="User",
        )

        self.assertFalse(user.email_verified)

    def test_default_bio_is_empty(self):
        user = User.objects.create_user(
            username="empty-bio",
            email="empty-bio@example.com",
            password=self.password,
            first_name="Empty",
            last_name="Bio",
        )

        self.assertEqual(user.bio, "")

    @patch(
        "apps.accounts.models.uuid4",
        return_value=SimpleNamespace(hex="fixeduuid"),
    )
    def test_avatar_upload_path_uses_user_id(
        self,
        mocked_uuid,
    ):
        path = user_directory_path(
            self.active_user,
            "MyPhoto.JPEG",
        )

        self.assertEqual(
            path,
            (
                f"avatars/{self.active_user.pk}/"
                "fixeduuid.jpeg"
            ),
        )

    @patch(
        "apps.accounts.models.uuid4",
        return_value=SimpleNamespace(hex="fixeduuid"),
    )
    def test_unsaved_user_avatar_path_uses_new(
        self,
        mocked_uuid,
    ):
        unsaved_user = User(
            username="draft-user",
        )

        path = user_directory_path(
            unsaved_user,
            "avatar.PNG",
        )

        self.assertEqual(
            path,
            "avatars/new/fixeduuid.png",
        )

    @patch(
        "apps.accounts.models.randint",
        return_value=7,
    )
    def test_random_default_avatar_path(
        self,
        mocked_randint,
    ):
        self.assertEqual(
            create_random_avatar(),
            "avatars/default/7.png",
        )

    def test_password_is_hashed(self):
        self.assertNotEqual(
            self.active_user.password,
            self.password,
        )
        self.assertTrue(
            self.active_user.check_password(
                self.password
            )
        )

    def test_required_fields_configuration(self):
        self.assertEqual(
            User.REQUIRED_FIELDS,
            [
                "first_name",
                "last_name",
                "email",
            ],
        )