from django import forms

from .models import Board

class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = (
            'title',
            'description',
        )
        
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'input',
                    'placeholder': 'مثلا توسعه Taskflow...',
                    'autocomplete': 'off',
                    'maxlength': 150,
                }
            ),
            
            'description': forms.Textarea(
                attrs={
                    'class': 'textarea',
                    'placeholder': 'توضیح کوتاهی درباره ی هدف این Board...',
                    'rows': 5,
                }
            ),
        }
        
    
    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        
        if len(title) < 3:
            raise forms.ValidationError(
                'عنوان Board باید حداقل 3 کاراکتر داشته باشد.'
            )
        
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        
        return description.strip()