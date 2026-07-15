from django import forms
from django.utils import timezone
from .models import Workspace, WorkspaceMembership, WorkspaceInvitation


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = (
            'name',
            'description',
        )
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'input',
                    'placeholder': 'مثلا پروژه TaskFlow...',
                    'autocomplete': 'off',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'textarea',
                    'placeholder': 'توضیح کوتاهی درباره این Workspace...',
                }
            ),
        }
        
    
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        
        if len(name) < 3:
            raise forms.ValidationError(
                'نام Workspace باید حداقل 3 کاراکتر باشد.'
            )
        
        return name

class WorkspaceInviteForm(forms.ModelForm):
    
    def __init__(
        self,
        *args,
        workspace=None,
        request_user=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.request_user = request_user
        
        self.fields['role'].choices = [
            choice
            for choice in WorkspaceMembership.Role.choices
            if choice[0] != WorkspaceMembership.Role.OWNER
        ]
    
    class Meta:
        model = WorkspaceInvitation
        fields = ('email', 'role')
        widgets = {
            'email': forms.EmailInput(
                attrs={
                    'class': 'input',
                    'placeholder': 'example@email.com',
                    'autocomplete': 'email',
                }
            ),
            'role': forms.Select(
                attrs={
                    'class': 'select',
                }
            ),
        }
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        
        if self.workspace is None:
            raise forms.ValidationError(
                'Workspace برای اعتبارسنجی دعوت مشخص نشده است.'
            )
        
        if self.request_user is None:
            raise forms.ValidationError(
                'کاربر ارسال کننده دعوت مشخص نشده است.'
            )
        
        if self.request_user.email.lower() == email:
            raise forms.ValidationError(
                'نمیتوانید خودتان را دعوت کنید.'
            )
        
        if WorkspaceMembership.objects.filter(
            workspace=self.workspace,
            user__email__iexact=email,
        ).exists():
            raise forms.ValidationError(
                'کاربر از قبل عضو Workspace است.'
            )
        
        if WorkspaceInvitation.objects.filter(
            workspace=self.workspace,
            email__iexact=email,
            status=WorkspaceInvitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        ).exists():
            raise forms.ValidationError(
                'برای این ایمیل یک دعوتنامه در انتظار وجود دارد.'
            )
        
        return email

    def clean_role(self):
        role = self.cleaned_data['role']
        
        if role == WorkspaceMembership.Role.OWNER:
            raise forms.ValidationError(
                'نمیتوان کاربر را با نقش مالک دعوت کرد.'
            )
        
        return role
    
class WorkspaceMembershipUpdateForm(forms.ModelForm):
    
    def __init__(
        self,
        *args,
        requester_role=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        
        self.requester_role = requester_role
        
        if (
            requester_role
            == WorkspaceMembership.Role.ADMIN
        ):
            self.fields['role'].choices = [
                choice
                for choice in WorkspaceMembership.Role.choices
                if choice[0] in {
                    WorkspaceMembership.Role.MEMBER,
                    WorkspaceMembership.Role.VIEWER,
                }
            ]
    class Meta:
        model = WorkspaceMembership
        fields = ('role', )
        widgets = {
            'role': forms.Select(
                attrs={
                    'class': 'select',
                }
            ),
        }
    
    def clean_role(self):
        role = self.cleaned_data['role']

        if role == WorkspaceMembership.Role.OWNER:
            raise forms.ValidationError(
                'انتقال مالکیت باید از بخش جداگانه انجام شود.'
            )
        
        if (
            self.requester_role
            == WorkspaceMembership.Role.ADMIN
            and role
            == WorkspaceMembership.Role.ADMIN
        ):
            raise forms.ValidationError(
                'فقط مالک Workspace میتواند نقش مدیر بدهد.'
            )
        
        return role