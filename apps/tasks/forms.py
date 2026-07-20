from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Task


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