from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        required=True,
        label="نام",
        widget=forms.widgets.TextInput(attrs={
            'class': 'input',
            'placeholder': 'نام...',
            'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        required=True,
        label='نام خانوادگی',
        widget=forms.widgets.TextInput(attrs={
            'class': 'input',
            'placeholder': 'نام خانوادگی...',
            'autocomplete': 'family-name',
        }),
    )
    
    username = forms.CharField(
        required=True,
        label='نام کاربری',
        widget=forms.widgets.TextInput(attrs={
            'class': 'input',
            'placeholder': 'نام کاربری...',
            'autocomplete': 'username',
        }),
    )
    
    email = forms.EmailField(
        required=True,
        label='ایمیل',
        widget=forms.widgets.EmailInput(attrs={
            'class': 'input',
            'placeholder': 'example@email.com',
            'autocomplete': 'email',
        }),
    )

    password1 = forms.CharField(
        label='رمز عبور',
        widget=forms.widgets.PasswordInput(attrs={
            'class': 'input',
            'placeholder': '........',
            'autocomplete': 'new-password',
        }),
    )
    
    password2 = forms.CharField(
        label='تکرار رمز عبور',
        widget=forms.widgets.PasswordInput(attrs={
            'class': 'input',
            'placeholder': '........',
            'autocomplete': 'new-password',
        }),
    )
    
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'username',
            'email',
            'password1',
            'password2',
        )
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('این ایمیل قبلا ثبت شده است.')
        
        return email

class ResendActivationEmailForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.widgets.EmailInput(attrs={
            'class': 'input',
            'placeholder': 'ایمیل...',
            'autocomplete': 'email',
        }),
    )
    
    def clean_email(self):
        return self.cleaned_data['email'].lower().strip()