from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from apps.boards.mixins import (
    BOARD_DELETE_ROLES,
    BOARD_WRITE_ROLES,
    BoardDeleteRequiredMixin,
    BoardObjectMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
)

from .forms import ColumnForm
from .mixins import (
    ArchivedColumnObjectMixin,
    ColumnObjectMixin,
)
from .models import Column
from .selectors import (
    get_archived_columns,
)
from .services import (
    ColumnLifecycleService,
)


class ColumnCreateView(
    BoardObjectMixin,
    BoardWriteRequiredMixin,
    CreateView,
):
    model = Column
    form_class = ColumnForm
    template_name = "columns/create.html"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        board = self.get_board()

        context.update(
            {
                "workspace": (
                    self.get_workspace()
                ),
                "board": board,
                "current_user_role": (
                    self.get_current_user_role()
                ),
                "next_position": (
                    Column.objects.next_position(
                        board=board,
                    )
                ),
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        (
            self.object,
            board,
        ) = ColumnLifecycleService.create(
            workspace=self.get_workspace(),
            board=self.get_board(),
            actor=self.request.user,
            title=form.cleaned_data["title"],
        )

        messages.success(
            self.request,
            (
                f"ستون «{self.object.title}» "
                "با موفقیت ساخته شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )


class ColumnUpdateView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    UpdateView,
):
    model = Column
    form_class = ColumnForm
    template_name = "columns/update.html"
    context_object_name = "column"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "workspace": (
                    self.get_workspace()
                ),
                "board": self.get_board(),
                "current_user_role": (
                    self.get_current_user_role()
                ),
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        (
            self.object,
            board,
        ) = ColumnLifecycleService.update(
            workspace=self.get_workspace(),
            board=self.get_board(),
            column=self.get_column(),
            title=form.cleaned_data["title"],
        )

        messages.success(
            self.request,
            (
                f"ستون «{self.object.title}» "
                "با موفقیت ویرایش شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )


class ArchivedColumnListView(
    BoardObjectMixin,
    BoardReadRequiredMixin,
    ListView,
):
    model = Column
    template_name = (
        "columns/archived_list.html"
    )
    context_object_name = "columns"
    paginate_by = 12

    def get_queryset(self):
        return get_archived_columns(
            board=self.get_board(),
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        current_user_role = (
            self.get_current_user_role()
        )

        context.update(
            {
                "workspace": (
                    self.get_workspace()
                ),
                "board": self.get_board(),
                "current_user_role": (
                    current_user_role
                ),
                "can_restore_columns": (
                    current_user_role
                    in BOARD_WRITE_ROLES
                ),
                "can_delete_columns": (
                    current_user_role
                    in BOARD_DELETE_ROLES
                ),
            }
        )

        return context


class ColumnArchiveView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = ["post"]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        (
            column,
            board,
        ) = ColumnLifecycleService.archive(
            workspace=self.get_workspace(),
            board=self.get_board(),
            column=self.get_column(),
        )

        messages.success(
            request,
            (
                f"ستون «{column.title}» "
                "با موفقیت آرشیو شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )


class ColumnRestoreView(
    ArchivedColumnObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = ["post"]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        (
            column,
            board,
        ) = ColumnLifecycleService.restore(
            workspace=self.get_workspace(),
            board=self.get_board(),
            column=self.get_column(),
        )

        messages.success(
            request,
            (
                f"ستون «{column.title}» "
                "با موفقیت بازیابی شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )


class ColumnDeleteView(
    ArchivedColumnObjectMixin,
    BoardDeleteRequiredMixin,
    DeleteView,
):
    model = Column
    template_name = (
        "columns/confirm_delete.html"
    )
    context_object_name = "column"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "workspace": (
                    self.get_workspace()
                ),
                "board": self.get_board(),
                "current_user_role": (
                    self.get_current_user_role()
                ),
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        (
            column_title,
            workspace_id,
            board_id,
        ) = ColumnLifecycleService.delete(
            workspace=self.get_workspace(),
            board=self.get_board(),
            column=self.object,
        )

        messages.success(
            self.request,
            (
                f"ستون «{column_title}» "
                "برای همیشه حذف شد."
            ),
        )

        return redirect(
            "columns:archived_list",
            workspace_pk=workspace_id,
            board_pk=board_id,
        )