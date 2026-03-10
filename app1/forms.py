from django import forms
from .models import LateCheckInPolicy
from django.core.exceptions import ValidationError

class LateCheckInPolicyForm(forms.ModelForm):
    class Meta:
        model = LateCheckInPolicy
        fields = ['student', 'start_time', 'description']
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        policy_id = self.instance.id  # Get the current instance's ID

        # Check if a LateCheckInPolicy already exists for this student, excluding the current instance
        if student and LateCheckInPolicy.objects.filter(student=student).exclude(id=policy_id).exists():
            raise ValidationError(f"A late check-in policy already exists for {student.name}.")
        
        return cleaned_data


from django import forms
from .models import Student

class StudentEditForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'name',
            'email',
            'phone_number',
            'student_class',
            'image',
            'roll_no',
            'address',
            'date_of_birth',
            'joining_date',
            'mother_name',
            'father_name'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'student_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter class'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'roll_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter roll number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter mother\'s name'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter father\'s name'}),
        }
