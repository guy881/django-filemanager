import mimetypes
import os
import re
import tarfile

from PIL import Image
from django.http import HttpResponse
from django.shortcuts import render

from . import settings
from .actions import handle_action
from .forms import FileManagerForm
from .utils import get_size

path_end = r'(?P<path>[\w\d_ -/.]*)$'


class FileManager(object):
    """
    maxspace,maxfilesize in KB
    """
    idee = 0

    def __init__(
        self,
        basepath,
        ckeditor_baseurl='',
        maxfolders=50,
        maxspace=5*1024,
        maxfilesize=5*1024,
        public_url_base=None,
        extensions=None,
    ):
        if basepath[-1] == '/':
            basepath = basepath[:-1]
        if ckeditor_baseurl and ckeditor_baseurl[-1] == '/':
            ckeditor_baseurl = ckeditor_baseurl[:-1]
        self.basepath = basepath
        self.ckeditor_baseurl = ckeditor_baseurl
        self.maxfolders = maxfolders
        self.maxspace = maxspace
        self.maxfilesize = maxfilesize
        self.extensions = extensions
        self.public_url_base = public_url_base

        self.config = {
            'FILEMANAGER_STATIC_ROOT': settings.FILEMANAGER_STATIC_ROOT,
            'FILEMANAGER_CKEDITOR_JS': settings.FILEMANAGER_CKEDITOR_JS,
            'FILEMANAGER_CHECK_SPACE': settings.FILEMANAGER_CHECK_SPACE,
            'FILEMANAGER_SHOW_SPACE': settings.FILEMANAGER_SHOW_SPACE,
            'maxfolders': self.maxfolders,
            'maxspace': self.maxspace,
            'maxfilesize': self.maxfilesize,
            'extensions': self.extensions,
            'basepath': self.basepath,
        }

    def next_id(self):
        self.idee = self.idee + 1
        return self.idee

    def handle_form(self, form, files):
        action = form.cleaned_data['action']
        path = form.cleaned_data['path']
        name = form.cleaned_data['name']
        file_or_dir = form.cleaned_data['file_or_dir']
        self.current_path = form.cleaned_data['current_path']
        messages = []

        invalid_folder_name = (
            name
            and file_or_dir == 'dir'
            and not re.match(r'[\w\d_ -]+', name).group(0) == name
        )
        if invalid_folder_name:
            messages.append("Invalid folder name : " + name)
            return messages

        invalid_file_name = (
            name
            and file_or_dir == 'file'
            and (
                re.search(r'\.\.', name)
                or not re.match(r'[\w\d_ -.]+', name).group(0) == name
            )
        )
        if invalid_file_name:
            messages.append("Invalid file name : " + name)
            return messages

        invalid_path = not re.match(r'[\w\d_ -/]+', path).group(0) == path
        if invalid_path:
            messages.append("Invalid path : " + path)
            return messages

        # actual handling of action
        handle_action(action, path, name, file_or_dir, files, self.current_path, messages, self.config)

        return messages

    def directory_structure(self):
        self.idee = 0
        dir_structure = {
            '': {
                'id': self.next_id(),
                'open': 'yes',
                'dirs': {},
                'files': [],
            },
        }
        os.chdir(self.basepath)
        for directory, directories, files in os.walk('.'):
            directory_list = directory[1:].split('/')
            current_dir = None
            nextdirs = dir_structure
            for d in directory_list:
                current_dir = nextdirs[d]
                nextdirs = current_dir['dirs']
            if directory[1:] + '/' == self.current_path:
                self.current_id = current_dir['id']
            current_dir['dirs'].update(
                dict(
                    map(
                        lambda d: (
                            d,
                            {
                                'id': self.next_id(),
                                'open': 'no',
                                'dirs': {},
                                'files': [],
                            }
                        ),
                        directories,
                    )
                )
            )
            current_dir['files'] = files
        return dir_structure

    def media(self, path):
        ext = path.split('.')[-1]
        try:
            mimetypes.init()
            mimetype = mimetypes.guess_type(path)[0]
            img = Image.open(self.basepath + '/' + path)
            width, height = img.size
            mx = max([width, height])
            w, h = width, height
            if mx > 60:
                w = width*60/mx
                h = height*60/mx
            img = img.resize((w, h), Image.ANTIALIAS)
            response = HttpResponse(content_type=mimetype or "image/" + ext)
            response['Cache-Control'] = 'max-age=3600'
            img.save(
                response,
                mimetype.split('/')[1] if mimetype else ext.upper()
            )
            return response
        except Exception:
            imagepath = (
                settings.FILEMANAGER_STATIC_ROOT
                + 'images/icons/'
                + ext
                + '.png'
            )
            if not os.path.exists(imagepath):
                imagepath = (
                    settings.FILEMANAGER_STATIC_ROOT
                    + 'images/icons/default.png'
                )
            img = Image.open(imagepath)
            width, height = img.size
            mx = max([width, height])
            w, h = width, height
            if mx > 60:
                w = int(width*60/mx)
                h = int(height*60/mx)
            img = img.resize((w, h), Image.ANTIALIAS)
            response = HttpResponse(content_type="image/png")
            response['Cache-Control'] = 'max-age:3600'
            img.save(response, 'png')
            return response

    def download(self, path, file_or_dir):
        if not re.match(r'[\w\d_ -/]*', path).group(0) == path:
            return HttpResponse('Invalid path')
        if file_or_dir == 'file':
            filepath = self.basepath + '/' + path
            with open(filepath, 'rb') as f:
                response = HttpResponse(
                    f.read(),
                    content_type=mimetypes.guess_type(filepath)[0],
                )
            response['Content-Length'] = os.path.getsize(filepath)
            response['Content-Disposition'] = (
                'attachment; filename=' + path.split('/')[-1]
            )
            return response
        elif file_or_dir == 'dir':
            dirpath = self.basepath + '/' + path
            dirname = dirpath.split('/')[-2]
            response = HttpResponse(content_type='application/x-gzip')
            response['Content-Disposition'] = (
                'attachment; filename=%s.tar.gz'
                % dirname
            )
            tarred = tarfile.open(fileobj=response, mode='w:gz')
            tarred.add(dirpath, arcname=dirname)
            tarred.close()
            return response

    def render(self, request, path):
        if 'download' in request.GET:
            return self.download(path, request.GET['download'])
        if path:
            return self.media(path)
        CKEditorFuncNum = request.GET.get('CKEditorFuncNum', '')
        messages = []
        self.current_path = '/'
        self.current_id = 1
        if request.method == 'POST':
            form = FileManagerForm(request.POST, request.FILES)
            if form.is_valid():
                messages = self.handle_form(form, request.FILES)
        if settings.FILEMANAGER_CHECK_SPACE:
                space_consumed = get_size(self.basepath)
        else:
                space_consumed = 0
        return render(
            request,
            'filemanager/index.html',
            {
                'dir_structure': self.directory_structure(),
                'messages': list(map(str, messages)),
                'current_id': self.current_id,
                'CKEditorFuncNum': CKEditorFuncNum,
                'ckeditor_baseurl': self.ckeditor_baseurl,
                'public_url_base': self.public_url_base,
                'space_consumed': space_consumed,
                'max_space': self.maxspace,
                'show_space': settings.FILEMANAGER_SHOW_SPACE,
            }
        )
