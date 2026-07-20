from django import forms

from .models import Column

class ColumnForm(forms.ModelForm):
    class Meta:
        model = Column
        fields = (
            'title',
        )
        
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'input',
                    'placeholder': (
                        'مثلا برای انجام، '
                        "درحال انجام یا تکمیل‌شده"
                    ),
                    'autocomplete': 'off',
                    'maxlength': 100,
                }
            ),
        }
    
    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        
        if len(title) < 2:
            raise forms.ValidationError(
                'عنوان ستون باید حداقل '
                "۲ کاراکتر داشته باشد."
            )
        
        
        return title