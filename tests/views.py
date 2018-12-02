from django.conf import settings
from django.shortcuts import render

from filemanager import FileManager
from forms import TestForm


def view(request, path):
    extensions = ['html', 'htm', 'zip', 'py', 'css', 'js', 'jpeg', 'jpg', 'png']
    fm = FileManager(settings.MEDIA_ROOT, extensions=extensions)
    return fm.render(request, path)


def widget_test_view(request):
    form = TestForm()
    return render(template_name='tests/widget_test.html', request=request, context={'form': form})
