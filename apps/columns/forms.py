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

class ColumnDragReorderForm(forms.Form):
    target_position = forms.IntegerField(
        min_value=0,
        error_messages={
            "required": (
                "جایگاه مقصد الزامی است."
            ),
            "invalid": (
                "جایگاه مقصد باید "
                "یک عدد صحیح باشد."
            ),
            "min_value": (
                "جایگاه مقصد "
                "نمی‌تواند منفی باشد."
            ),
        },
    )
    
    def clean_target_position(self):
        raw_target_position = (
            self.data.get(
                'target_position'
            )
        )
        
        if (
            isinstance(
                raw_target_position,
                bool,
            )
            or not isinstance(
                raw_target_position,
                int,
            )
        ):
            raise forms.ValidationError(
                "جایگاه مقصد باید "
                "یک عدد صحیح باشد."
            )
    
        return self.cleaned_data['target_position']