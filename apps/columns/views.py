import json

from django.contrib import messages
from django.core.exceptions import (
    ValidationError,
)
from django.http import JsonResponse
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

from .forms import (
    ColumnDragReorderForm,
    ColumnForm,
)
from .mixins import (
    ArchivedColumnObjectMixin,
    ColumnObjectMixin,
)
from .models import Column
from .reordering import (
    ColumnReorderingService,
)
from .selectors import (
    get_archived_columns,
    serialize_board_columns,
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

class ColumnRelativeMoveView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    service_method_name = None
    success_message = None
    
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        service_method = getattr(
            ColumnReorderingService,
            self.service_method_name,
        )
        
        (
            column,
            board,
            changed,
        ) = service_method(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
        )
        
        if changed:
            messages.success(
                request,
                self.success_message.format(
                    title=column.title,
                ),
            )
        else:
            messages.info(
                request,
                (
                    f"ستون «{column.title}» "
                    "در همین جایگاه باقی ماند."
                ),
            )
        
        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )

class ColumnMoveLeftView(
    ColumnRelativeMoveView,
):
    service_method_name = "move_left"

    success_message = (
        "ستون «{title}» به جایگاه "
        "قبلی منتقل شد."
    )


class ColumnMoveRightView(
    ColumnRelativeMoveView,
):
    service_method_name = "move_right"

    success_message = (
        "ستون «{title}» به جایگاه "
        "بعدی منتقل شد."
    )

class ColumnDragReorderView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        "post",
    ]

    @staticmethod
    def _error_response(
        errors,
        *,
        status=400,
    ):
        return JsonResponse(
            {
                "ok": False,
                "errors": errors,
            },
            status=status,
        )

    @classmethod
    def _parse_payload(
        cls,
        request,
    ):
        try:
            raw_body = (
                request.body
                .decode("utf-8")
                .strip()
            )

        except UnicodeDecodeError:
            return (
                None,
                {
                    "__all__": [
                        (
                            "بدنه درخواست "
                            "قابل خواندن نیست."
                        ),
                    ],
                },
            )

        if not raw_body:
            return {}, None

        try:
            payload = json.loads(
                raw_body
            )

        except json.JSONDecodeError:
            return (
                None,
                {
                    "__all__": [
                        (
                            "ساختار JSON "
                            "درخواست معتبر نیست."
                        ),
                    ],
                },
            )

        if not isinstance(
            payload,
            dict,
        ):
            return (
                None,
                {
                    "__all__": [
                        (
                            "بدنه درخواست باید "
                            "یک JSON object باشد."
                        ),
                    ],
                },
            )

        return payload, None

    @staticmethod
    def _serialize_form_errors(
        form,
    ):
        return {
            field_name: [
                str(error)
                for error in error_list
            ]
            for (
                field_name,
                error_list,
            ) in form.errors.items()
        }

    @staticmethod
    def _serialize_validation_error(
        error,
    ):
        try:
            message_dict = (
                error.message_dict
            )

        except AttributeError:
            return {
                "__all__": [
                    str(message)
                    for message in (
                        error.messages
                    )
                ],
            }

        return {
            field_name: [
                str(message)
                for message in error_messages
            ]
            for (
                field_name,
                error_messages,
            ) in message_dict.items()
        }

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        board = self.get_board()
        scoped_column = self.get_column()

        (
            payload,
            payload_errors,
        ) = self._parse_payload(
            request
        )

        if payload_errors:
            return self._error_response(
                payload_errors,
            )

        form = ColumnDragReorderForm(
            data=payload,
        )

        if not form.is_valid():
            return self._error_response(
                self._serialize_form_errors(
                    form
                ),
            )

        try:
            (
                column,
                board,
                changed,
            ) = (
                ColumnReorderingService
                .reorder(
                    workspace=(
                        self.get_workspace()
                    ),
                    board_pk=board.pk,
                    column_pk=(
                        scoped_column.pk
                    ),
                    target_position=(
                        form.cleaned_data[
                            "target_position"
                        ]
                    ),
                )
            )

        except ValidationError as error:
            return self._error_response(
                self._serialize_validation_error(
                    error
                ),
            )

        return JsonResponse(
            {
                "ok": True,
                "changed": changed,
                "message": (
                    f"ستون «{column.title}» "
                    "با موفقیت جابه‌جا شد."
                    if changed
                    else (
                        f"ستون «{column.title}» "
                        "در همین جایگاه باقی ماند."
                    )
                ),
                "column": {
                    "id": column.pk,
                    "position": (
                        column.position
                    ),
                },
                "columns": (
                    serialize_board_columns(
                        board=board,
                    )
                ),
            }
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