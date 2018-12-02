from django.db import models

from filemanager.models import CKEditorField


class TestModel(models.Model):
    content = CKEditorField(filemanager_url='/app/abc/')
