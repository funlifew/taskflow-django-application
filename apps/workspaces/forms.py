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
        return self.cleaned_data['email'].lower().strip()

class WorkspaceMembershipUpdateFomr(forms.ModelForm):
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