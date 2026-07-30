from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import BoardForm
from .mixins import (
    ArchiveBoardObjectMixin,
    BOARD_DELETE_ROLES,
    BOARD_WRITE_ROLES,
    BoardDeleteRequiredMixin,
    BoardObjectMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
)
from .models import Board
from .selectors import (
    get_active_boards,
    get_archived_boards,
    get_archived_columns_count,
    get_board_detail_queryset,
)
from .services import BoardLifecycleService


class BoardListView(
    BoardReadRequiredMixin,
    ListView,
):
    model = Board
    template_name = "boards/list.html"
    context_object_name = "boards"
    paginate_by = 12

    def get_queryset(self):
        return get_active_boards(
            workspace=self.get_workspace(),
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        workspace = self.get_workspace()
        current_user_role = (
            self.get_current_user_role()
        )

        context.update(
            {
                "workspace": workspace,
                "current_user_role": (
                    current_user_role
                ),
                "can_create_board": (
                    current_user_role
                    in BOARD_WRITE_ROLES
                ),
                "archived_boards_count": (
                    get_archived_boards(
                        workspace=workspace,
                    ).count()
                ),
            }
        )

        return context


class BoardCreateView(
    BoardWriteRequiredMixin,
    CreateView,
):
    model = Board
    form_class = BoardForm
    template_name = "boards/create.html"

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context["workspace"] = (
            self.get_workspace()
        )

        return context

    def form_valid(
        self,
        form,
    ):
        workspace = self.get_workspace()

        self.object = (
            BoardLifecycleService.create(
                workspace=workspace,
                actor=self.request.user,
                title=form.cleaned_data["title"],
                description=(
                    form.cleaned_data[
                        "description"
                    ]
                ),
            )
        )

        messages.success(
            self.request,
            (
                f"Board «{self.object.title}» "
                "با موفقیت ساخته شد."
            ),
        )

        return redirect(
            "boards:list",
            workspace_pk=workspace.pk,
        )


class BoardDetailView(
    BoardObjectMixin,
    BoardReadRequiredMixin,
    DetailView,
):
    model = Board
    template_name = "boards/detail.html"
    context_object_name = "board"

    def get_board_queryset(self):
        return get_board_detail_queryset(
            queryset=(
                super()
                .get_board_queryset()
            ),
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

        can_edit_board = (
            current_user_role
            in BOARD_WRITE_ROLES
        )

        can_delete_board = (
            current_user_role
            in BOARD_DELETE_ROLES
        )

        columns = self.object.active_columns

        tasks_count = sum(
            len(column.active_tasks)
            for column in columns
        )

        context.update(
            {
                "workspace": (
                    self.get_workspace()
                ),
                "current_user_role": (
                    current_user_role
                ),
                "can_edit_board": (
                    can_edit_board
                ),
                "can_delete_board": (
                    can_delete_board
                ),
                "can_archive_board": (
                    can_edit_board
                ),
                "can_create_column": (
                    can_edit_board
                ),
                "can_update_columns": (
                    can_edit_board
                ),
                "can_archive_columns": (
                    can_edit_board
                ),
                "can_create_tasks": (
                    can_edit_board
                ),
                "can_drag_tasks": (
                    can_edit_board
                ),
                "columns": columns,
                "columns_count": len(columns),
                "archived_columns_count": (
                    get_archived_columns_count(
                        board=self.object,
                    )
                ),
                "tasks_count": tasks_count,
            }
        )

        return context


class BoardUpdateView(
    BoardObjectMixin,
    BoardWriteRequiredMixin,
    UpdateView,
):
    model = Board
    form_class = BoardForm
    template_name = "boards/update.html"
    context_object_name = "board"

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
        self.object = (
            BoardLifecycleService.update(
                workspace=self.get_workspace(),
                board=self.get_board(),
                title=form.cleaned_data["title"],
                description=(
                    form.cleaned_data[
                        "description"
                    ]
                ),
            )
        )

        messages.success(
            self.request,
            (
                f"Board «{self.object.title}» "
                "با موفقیت ویرایش شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=(
                self.object.workspace_id
            ),
            board_pk=self.object.pk,
        )


class ArchivedBoardListView(
    BoardReadRequiredMixin,
    ListView,
):
    model = Board
    template_name = "boards/archived_list.html"
    context_object_name = "boards"
    paginate_by = 12

    def get_queryset(self):
        return get_archived_boards(
            workspace=self.get_workspace(),
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
                "current_user_role": (
                    current_user_role
                ),
                "can_restore_boards": (
                    current_user_role
                    in BOARD_WRITE_ROLES
                ),
                "can_delete_boards": (
                    current_user_role
                    in BOARD_DELETE_ROLES
                ),
            }
        )

        return context


class BoardArchiveView(
    BoardObjectMixin,
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
        board = BoardLifecycleService.archive(
            workspace=self.get_workspace(),
            board=self.get_board(),
        )

        messages.success(
            request,
            (
                f"Board «{board.title}» "
                "با موفقیت آرشیو شد."
            ),
        )

        return redirect(
            "boards:list",
            workspace_pk=board.workspace_id,
        )


class BoardRestoreView(
    ArchiveBoardObjectMixin,
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
        board = BoardLifecycleService.restore(
            workspace=self.get_workspace(),
            board=self.get_board(),
        )

        messages.success(
            request,
            (
                f"Board «{board.title}» "
                "با موفقیت بازیابی شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )


class BoardDeleteView(
    ArchiveBoardObjectMixin,
    BoardDeleteRequiredMixin,
    DeleteView,
):
    model = Board
    template_name = (
        "boards/confirm_delete.html"
    )
    context_object_name = "board"

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
            board_title,
            workspace_id,
        ) = BoardLifecycleService.delete(
            workspace=self.get_workspace(),
            board=self.object,
        )

        messages.success(
            self.request,
            (
                f"Board «{board_title}» "
                "برای همیشه حذف شد."
            ),
        )

        return redirect(
            "boards:archived_list",
            workspace_pk=workspace_id,
        )