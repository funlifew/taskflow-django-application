from django.urls import reverse

from .base import DashboardTestBase


class ApplicationShellUITests(
    DashboardTestBase
):
    def setUp(self):
        super().setUp()

        self.client.force_login(
            self.user
        )

    def get_dashboard_response(self):
        return self.client.get(
            reverse(
                "dashboard:dashboard"
            )
        )

    def test_dashboard_loads_stabilization_styles(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "css/ui-stabilization.css",
        )

    def test_heavy_space_scene_is_not_rendered(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertNotContains(
            response,
            "data-app-space",
        )

        self.assertNotContains(
            response,
            "app-space-scene",
        )

        self.assertNotContains(
            response,
            "pointer-glow",
        )

        self.assertNotContains(
            response,
            "js/space-scene.js",
        )

    def test_drawer_is_rendered_before_app_shell(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        html = (
            response.content
            .decode("utf-8")
        )

        drawer_position = (
            html.index(
                'data-drawer'
            )
        )

        shell_position = (
            html.index(
                'data-app-shell'
            )
        )

        self.assertLess(
            drawer_position,
            shell_position,
        )

    def test_drawer_has_independent_scroll_region(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertContains(
            response,
            "data-drawer-panel",
        )

        self.assertContains(
            response,
            "data-drawer-scroll",
        )

        self.assertContains(
            response,
            'id="mobile-navigation-drawer"',
        )

    def test_drawer_openers_reference_drawer(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertContains(
            response,
            "data-drawer-open",
            count=2,
        )

        self.assertContains(
            response,
            (
                'aria-controls='
                '"mobile-navigation-drawer"'
            ),
            count=2,
        )

        self.assertContains(
            response,
            'aria-expanded="false"',
            count=2,
        )

    def test_navigation_has_no_coming_soon_items(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertNotContains(
            response,
            "به‌زودی",
        )

        self.assertNotContains(
            response,
            "nav-link--disabled",
        )

        self.assertNotContains(
            response,
            "nav-soon",
        )

    def test_navigation_contains_real_routes(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertContains(
            response,
            reverse(
                "dashboard:dashboard"
            ),
        )

        self.assertContains(
            response,
            reverse(
                "workspaces:list"
            ),
        )

        self.assertContains(
            response,
            reverse(
                "notifications:list"
            ),
        )

        self.assertContains(
            response,
            reverse(
                "dashboard:profile"
            ),
        )

    def test_shared_navigation_is_used_twice(
        self,
    ):
        response = (
            self.get_dashboard_response()
        )

        self.assertContains(
            response,
            'data-nav="dashboard"',
            count=3,
        )

        self.assertContains(
            response,
            'data-nav="workspaces"',
            count=3,
        )

        self.assertContains(
            response,
            'data-nav="profile"',
            count=3,
        )

        self.assertContains(
            response,
            'data-nav="notifications"',
            count=2,
        )