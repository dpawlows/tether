from django import forms
from .models import Journal


class NewJournalForm(forms.Form):
    codeword = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Choose a codeword'}),
        label="Codeword",
    )
    codeword_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm codeword'}),
        label="Confirm Codeword",
    )

    def clean(self):
        cleaned_data = super().clean()
        codeword = cleaned_data.get('codeword')
        codeword_confirm = cleaned_data.get('codeword_confirm')
        if codeword and codeword_confirm and codeword != codeword_confirm:
            raise forms.ValidationError("Codewords do not match.")
        return cleaned_data


class OpenJournalForm(forms.Form):
    codeword = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your codeword'}),
        label="Codeword",
    )


class EntryForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Write here...'}),
        label="",
    )


class FrontMatterForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ['player1_name', 'player2_name', 'date_ended']
        widgets = {
            'player1_name': forms.TextInput(attrs={'class': 'fm-input', 'autocomplete': 'off'}),
            'player2_name': forms.TextInput(attrs={'class': 'fm-input', 'autocomplete': 'off'}),
            'date_ended':   forms.TextInput(attrs={'class': 'fm-input', 'autocomplete': 'off'}),
        }
        labels = {
            'player1_name': '',
            'player2_name': '',
            'date_ended':   '',
        }


class MapForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ['map_notes']
        widgets = {
            'map_notes': forms.Textarea(attrs={'class': 'map-textarea', 'placeholder': ''}),
        }
        labels = {'map_notes': ''}
