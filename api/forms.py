from django import forms
from .models import SiteSettings


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ['gst', 'pst', 'cpp', 'ei_ee', 'ei_er']

        labels = {
            'gst': 'GST Rate (%)',
            'pst': 'PST Rate (%)',
            'cpp': 'CPP Rate (%)',
            'ei_ee': 'EI Employee Rate (%)',
            'ei_er': 'EI Employer Rate (%)',
        }

        widgets = {
            'gst': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.0001',
                'placeholder': '5.0000'
            }),
            'pst': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.0001',
                'placeholder': '7.0000'
            }),
            'cpp': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.0001',
                'placeholder': '5.9500'
            }),
            'ei_ee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.0001',
                'placeholder': '1.6300'
            }),
            'ei_er': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.0001',
                'placeholder': '2.2820'
            }),
        }