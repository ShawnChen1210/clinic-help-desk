from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'}))

class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'}),
            'email': forms.EmailInput(attrs={'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'}),
            'first_name': forms.TextInput(attrs={'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'}),
            'last_name': forms.TextInput(attrs={'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # doing this for the password fields because nothing else works
        self.fields['password1'].widget.attrs.update({
            'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'm-1 p-1 border border-gray-400 rounded-md focus:outline-none'
        })

    #save() override, so that it also saves email, first and last name
    def save(self, commit=True):
        user = super().save(commit=False) #creates a user object, but doesn't save it to database yet
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
