from django import forms

class RegistrationForm(forms.Form):
    First_Name = forms.CharField(label='First Name', max_length=100)
    Last_Name = forms.CharField(label='Last Name', max_length=100)
    Email = forms.EmailField(label='Email')
    Password = forms.CharField(label='Password', max_length=100)
    Confirm_Password = forms.CharField(label='Confirm Password', max_length=100)