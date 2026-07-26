from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.columns.models import Column
from apps.workspaces.models import WorkspaceMembership

from .models import Task
from .constants import TASK_ASSIGNABLE_ROLES


User = get_user_model()


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task

        fields = (
            "title",
            "description",
            "priority",
            "assignee",
            "due_at",
        )

        labels = {
            "title": "عنوان Task",
            "description": "توضیحات",
            "priority": "اولویت",
            "assignee": "مسئول",
            "due_at": "مهلت انجام",
        }

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "مثلاً طراحی صفحه ورود",
                    "autocomplete": "off",
                    "maxlength": 200,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "input",
                    "placeholder": "جزئیات Task را بنویس...",
                    "rows": 5,
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "assignee": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "due_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "input",
                    "type": "datetime-local",
                },
            ),
        }

    def __init__(
        self,
        *args,
        workspace=None,
        **kwargs,
    ):
        self.workspace = workspace

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "assignee"
        ].empty_label = "بدون مسئول"

        self.fields[
            "due_at"
        ].input_formats = (
            "%Y-%m-%dT%H:%M",
        )

        if workspace is None:
            self.fields[
                "assignee"
            ].queryset = User.objects.none()

            return

        self.fields[
            "assignee"
        ].queryset = (
            User.objects
            .filter(
                Q(
                    pk=workspace.owner_id,
                )
                | Q(
                    workspace_memberships__workspace=(
                        workspace
                    ),
                    workspace_memberships__role__in=(
                        TASK_ASSIGNABLE_ROLES
                    ),
                )
            )
            .distinct()
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

    def clean_title(self):
        title = self.cleaned_data[
            "title"
        ].strip()

        if len(title) < 2:
            raise forms.ValidationError(
                "عنوان Task باید حداقل "
                "۲ کاراکتر داشته باشد."
            )

        return title


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            'status',
        )
        
        widgets = {
            'status': forms.Select(
                attrs={
                    'class': 'input',
                }
            ),
        }

class TaskMoveForm(forms.Form):
    target_column = forms.ModelChoiceField(
        label='ستون مقصد',
        queryset=Column.objects.none(),
        widget=forms.Select(
            attrs={
                'class': 'input',
            }
        ),
    )
    
    
    def __init__(
        self,
        *args,
        board=None,
        current_column=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        
        self.board = board
        self.current_column = current_column
        
        if board is None:
            return
        
        queryset = (
            Column.objects
            .active()
            .for_board(board)
            .order_by(
                'position',
                'pk',
            )
        )
        
        if current_column is not None:
            queryset = queryset.exclude(
                pk=current_column.pk,
            )
        
        self.fields['target_column'].queryset = queryset

class TaskReorderForm(forms.Form):
    target_column = forms.ModelChoiceField(
        label="ستون مقصد",
        queryset=Column.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "input",
            }
        ),
        help_text=(
            "برای جابه‌جایی داخل همین ستون، "
            "ستون فعلی را انتخاب کن."
        ),
    )

    target_position = forms.IntegerField(
        label="جایگاه مقصد",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "input",
                "min": 1,
                "step": 1,
            }
        ),
        help_text=(
            "عدد ۱ یعنی ابتدای ستون."
        ),
    )

    def __init__(
        self,
        *args,
        board=None,
        task=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.board = board
        self.task = task

        if board is None:
            self.fields[
                "target_column"
            ].queryset = (
                Column.objects.none()
            )

            return

        self.fields[
            "target_column"
        ].queryset = (
            Column.objects
            .active()
            .for_board(board)
            .order_by(
                "position",
                "pk",
            )
        )

        if (
            task is not None
            and not self.is_bound
        ):
            self.initial.update(
                {
                    "target_column": (
                        task.column
                    ),
                    "target_position": (
                        task.position + 1
                    ),
                }
            )

    def clean(self):
        cleaned_data = super().clean()

        target_column = (
            cleaned_data.get(
                "target_column"
            )
        )

        target_position = (
            cleaned_data.get(
                "target_position"
            )
        )

        if (
            target_column is None
            or target_position is None
            or self.task is None
        ):
            return cleaned_data

        same_column = (
            target_column.pk
            == self.task.column_id
        )

        target_task_count = (
            Task.objects
            .active()
            .for_column(
                target_column
            )
            .count()
        )

        if same_column:
            maximum_user_position = (
                target_task_count
            )
        else:
            maximum_user_position = (
                target_task_count + 1
            )

        if (
            target_position
            > maximum_user_position
        ):
            self.add_error(
                "target_position",
                (
                    "بیشترین جایگاه مجاز "
                    "برای این ستون "
                    f"{maximum_user_position} است."
                ),
            )

            return cleaned_data

        cleaned_data[
            "target_position"
        ] = target_position - 1

        return cleaned_data