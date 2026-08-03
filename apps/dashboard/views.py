from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.contrib.messages.views import (
    SuccessMessageMixin,
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    TemplateView,
    UpdateView,
)

from apps.notifications.selectors import (
    get_recent_notifications,
)

from .forms import ProfileUpdateForm
from .metrics import (
    get_user_board_summaries,
    get_user_dashboard_summary,
    get_user_task_progress,
    get_user_workspace_summaries,
)
from .selectors import (
    get_user_due_soon_tasks,
    get_user_overdue_tasks,
    get_user_recent_task_activities,
    get_user_recent_tasks,
)


class DashboardView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = (
        "dashboard/dashboard.html"
    )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        user = self.request.user
        now = timezone.now()

        context.update(
            {
                "summary": (
                    get_user_dashboard_summary(
                        user=user,
                        now=now,
                    )
                ),
                "user_progress": (
                    get_user_task_progress(
                        user=user,
                    )
                ),
                "assigned_tasks": (
                    get_user_recent_tasks(
                        user=user,
                        limit=6,
                    )
                ),
                "overdue_tasks": (
                    get_user_overdue_tasks(
                        user=user,
                        now=now,
                    )[:6]
                ),
                "due_soon_tasks": (
                    get_user_due_soon_tasks(
                        user=user,
                        now=now,
                        days=7,
                    )[:6]
                ),
                "workspace_summaries": (
                    get_user_workspace_summaries(
                        user=user,
                        now=now,
                        limit=6,
                    )
                ),
                "board_summaries": (
                    get_user_board_summaries(
                        user=user,
                        now=now,
                        limit=6,
                    )
                ),
                "recent_activities": (
                    get_user_recent_task_activities(
                        user=user,
                        limit=10,
                    )
                ),
                "recent_notifications": (
                    get_recent_notifications(
                        user=user,
                        limit=6,
                    )
                ),
            }
        )

        return context


class ProfileView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = (
        "dashboard/profile.html"
    )


class ProfileUpdateView(
    LoginRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    form_class = ProfileUpdateForm
    template_name = (
        "dashboard/profile_update.html"
    )
    success_url = reverse_lazy(
        "dashboard:profile"
    )
    success_message = (
        "پروفایل شما با موفقیت "
        "به روزرسانی شد."
    )

    def get_object(
        self,
        queryset=None,
    ):
        return self.request.user