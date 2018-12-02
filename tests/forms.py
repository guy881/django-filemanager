from django import forms

from filemanager.widgets import CKEditorWidget


class TestForm(forms.Form):
    name = forms.CharField(max_length=32)
    content = CKEditorWidget(filemanager_url='/abc/')

