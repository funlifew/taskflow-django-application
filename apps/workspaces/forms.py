from django import forms
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
        ).exists():
            raise forms.ValidationError(
                'برای این ایمیل یک دعوتنامه در انتظار وجود دارد.'
            )
        
        return email

class WorkspaceMembershipUpdateForm(forms.ModelForm):
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
        
        return role