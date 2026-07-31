from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

ALLOWED_AVATAR_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/jpg",
        "image/webp",
        "image/gif",
    }
)

MAX_AVATAR_SIZE_BYTES = (
    5 * 1024 * 1024
)
class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='نام',
        widget=forms.widgets.TextInput(attrs={
            'class': 'input',
            'placeholder': 'نام...',
            'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='نام خانوادگی',
        widget=forms.widgets.TextInput(attrs={
            'class': 'input',
            'placeholder': 'نام خانوادگی...',
            'autocomplete': 'family-name',
        }),
    )
    username = forms.CharField(
        label='نام کاربری',
        required=True,
        max_length=150,
        widget=forms.widgets.TextInput(
            attrs={
                'class': 'input',
                'placeholder': 'نام کاربری...',
                'autocomplete': 'username',
            }
        ),
    )
    
    bio = forms.CharField(
        label='درباره من',
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                'class': 'textarea',
                'placeholder': 'مثلا Back-End Developer and Interested in Physics...',
                'rows': 5,
            }
        ),
    )
    
    avatar = forms.ImageField(
        label='تصویر پروفایل',
        required=False,
        widget=forms.FileInput(
            attrs={
                'data-avatar-input-v4': "",
                'accept': 'image/jpeg,image/png,image/jpg,image/webp,image/gif',
            }
        ),
    )
    
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'avatar',
            'bio',
        ]
        
    
    def clean_username(self):
        username = (
            self.cleaned_data[
                "username"
            ]
            .strip()
        )

        duplicate_exists = (
            User.objects
            .filter(
                username__iexact=username,
            )
            .exclude(
                pk=self.instance.pk,
            )
            .exists()
        )

        if duplicate_exists:
            raise forms.ValidationError(
                (
                    "این نام کاربری قبلاً "
                    "ثبت شده است."
                )
            )

        return username
    
    
    def clean_avatar(self):
        avatar = self.cleaned_data.get(
            "avatar"
        )

        if (
            not avatar
            or not hasattr(
                avatar,
                "content_type",
            )
        ):
            return avatar

        if (
            avatar.content_type
            not in ALLOWED_AVATAR_CONTENT_TYPES
        ):
            raise forms.ValidationError(
                (
                    "فقط تصاویر "
                    "JPG/JPEG/PNG/WEBP/GIF "
                    "مجاز هستند."
                )
            )

        if avatar.size > MAX_AVATAR_SIZE_BYTES:
            raise forms.ValidationError(
                (
                    "حجم تصویر نباید بیشتر "
                    "از 5 مگابایت باشد."
                )
            )

        return avatar