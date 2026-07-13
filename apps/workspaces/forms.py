from django import forms
from .models import Workspace


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