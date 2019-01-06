import mimetypes
import os
import re
import shutil
import zipfile

import magic

from .utils import get_size, rename_if_exists


class Action:

    def __init__(self, action, path, name, file_or_dir, files, current_path, messages, config):
        self.action = action
        self.path = path
        self.name = name
        self.file_or_dir = file_or_dir
        self.files = files
        self.current_path = current_path
        self.messages = messages
        self.config = config

    def process_action(self):
        pass


class UploadAction(Action):
    def process_action(self):
        for f in self.files.getlist('ufile'):

            self.validate_file(f)
            if len(self.messages) == 0:
                filename = f.name.replace(' ', '_')  # replace spaces to prevent fs error
                filepath = (
                        self.config['basepath']
                        + self.path
                        + rename_if_exists(self.config['basepath'] + self.path, filename)
                )
                with open(filepath, 'wb') as dest:
                    for chunk in f.chunks():
                        dest.write(chunk)
                f.close()
                mimetype = magic.from_file(filepath, mime=True)
                guessed_exts = mimetypes.guess_all_extensions(mimetype)
                guessed_exts = [ext[1:] for ext in guessed_exts]
                common = [ext for ext in guessed_exts if ext in self.config['extensions']]
                if not common:
                    os.remove(filepath)
                    self.messages.append(
                        "File type not allowed : "
                        + f.name
                    )
        if len(self.messages) == 0:
            self.messages.append('All files uploaded successfully')

        return self.messages

    def validate_file(self, f):
        file_name_invalid = (
                re.search(r'\.\.', f.name)
                or not re.match(r'[\w\d_ -/.]+', f.name).group(0) == f.name
        )
        if file_name_invalid:
            self.messages.append("File name is not valid : " + f.name)
        elif f.size > self.config['maxfilesize'] * 1024:
            self.messages.append(
                "File size exceeded "
                + str(self.config['maxfilesize'])
                + " KB : "
                + f.name
            )
        elif (
                self.config['FILEMANAGER_CHECK_SPACE'] and
                (
                        (get_size(self.config['basepath']) + f.size)
                        > self.config['maxspace'] * 1024
                )
        ):
            self.messages.append(
                "Total Space size exceeded "
                + str(self.config['maxspace'])
                + " KB : "
                + f.name
            )
        elif (
                self.config['extensions']
                and len(f.name.split('.')) > 1
                and f.name.split('.')[-1] not in self.config['extensions']
        ):
            self.messages.append(
                "File extension not allowed (."
                + f.name.split('.')[-1]
                + ") : "
                + f.name
            )
        elif (
                self.config['extensions']
                and len(f.name.split('.')) == 1
                and f.name.split('.')[-1]
                not in self.config['extensions']
        ):
            self.messages.append(
                "No file extension in uploaded file : "
                + f.name
            )


class RenameAction(Action):
    def process_action(self):

        # directory
        if self.file_or_dir == 'dir':
            oldname = self.path.split('/')[-2]
            path = '/'.join(self.path.split('/')[:-2])
            try:
                os.chdir(self.config['basepath'] + path)
                os.rename(oldname, self.name)
                self.messages.append(
                    'Folder renamed successfully from '
                    + oldname
                    + ' to '
                    + self.name
                )
            except OSError:
                self.messages.append('Folder couldn\'t renamed to ' + self.name)
            except Exception as e:
                self.messages.append('Unexpected error : ' + e)

                # file
        if self.file_or_dir == 'file':
            oldname = self.path.split('/')[-1]
            old_ext = (
                oldname.split('.')[1]
                if len(oldname.split('.')) > 1
                else None
            )
            new_ext = self.name.split('.')[1] if len(self.name.split('.')) > 1 else None
            if old_ext == new_ext:
                self.path = '/'.join(self.path.split('/')[:-1])
                try:
                    os.chdir(self.config['basepath'] + self.path)
                    os.rename(oldname, self.name)
                    self.messages.append(
                        'File renamed successfully from '
                        + oldname
                        + ' to '
                        + self.name
                    )
                except OSError:
                    self.messages.append('File couldn\'t be renamed to ' + self.name)
                except Exception as e:
                    self.messages.append('Unexpected error : ' + e)
            else:
                if old_ext:
                    self.messages.append(
                        'File extension should be same : .'
                        + old_ext
                    )
                else:
                    self.messages.append(
                        'New file extension didn\'t match with old file'
                        + ' extension'
                    )

        return self.messages


class DeleteAction(Action):
    def process_action(self):
        if self.file_or_dir == 'dir':
            if self.path == '/':
                self.messages.append('root folder can\'t be deleted')
            else:
                name = self.path.split('/')[-2]
                self.path = '/'.join(self.path.split('/')[:-2])
                try:
                    os.chdir(self.config['basepath'] + self.path)
                    shutil.rmtree(name)
                    self.messages.append('Folder deleted successfully : ' + name)
                except OSError:
                    self.messages.append('Folder couldn\'t deleted : ' + name)
                except Exception as e:
                    self.messages.append('Unexpected error : ' + e)

        elif self.file_or_dir == 'file':
            if self.path == '/':
                self.messages.append('root folder can\'t be deleted')
            else:
                name = self.path.split('/')[-1]
                self.path = '/'.join(self.path.split('/')[:-1])
                try:
                    os.chdir(self.config['basepath'] + self.path)
                    os.remove(name)
                    self.messages.append('File deleted successfully : ' + name)
                except OSError:
                    self.messages.append('File couldn\'t deleted : ' + name)
                except Exception as e:
                    self.messages.append('Unexpected error : ' + e)

        return self.messages


class AddAction(Action):
    def process_action(self):
        os.chdir(self.config['basepath'])
        no_of_folders = len(list(os.walk('.')))
        if (no_of_folders + 1) <= self.config['maxfolders']:
            try:
                os.chdir(self.config['basepath'] + self.path)
                os.mkdir(self.name)
                self.messages.append('Folder created successfully : ' + self.name)
            except OSError:
                self.messages.append('Folder couldn\'t be created : ' + self.name)
            except Exception as e:
                self.messages.append('Unexpected error : ' + e)
        else:
            self.messages.append(
                'Folder couldn\' be created because maximum number of '
                + 'folders exceeded : '
                + str(self.config['maxfolders'])
            )

        return self.messages


class MoveAction(Action):
    def process_action(self):
        # from path to current_path
        if self.current_path.find(self.path) == 0:
            self.messages.append('Cannot move/copy to a child folder')
        else:
            self.path = os.path.normpath(self.path)  # strip trailing slash if any
            filename = (
                    self.config['basepath']
                    + self.current_path
                    + os.path.basename(self.path)
            )
            if os.path.exists(filename):
                self.messages.append(
                    'ERROR: A file/folder with this name already exists in'
                    + ' the destination folder.'
                )
            else:
                if self.action == 'move':
                    method = shutil.move
                else:
                    if self.file_or_dir == 'dir':
                        method = shutil.copytree
                    else:
                        method = shutil.copy
                try:
                    method(self.config['basepath'] + self.path, filename)
                except OSError:
                    self.messages.append(
                        'File/folder couldn\'t be moved/copied.'
                    )
                except Exception as e:
                    self.messages.append('Unexpected error : ' + e)

        return self.messages


class CopyAction(MoveAction):
    pass


class UnzipAction(Action):
    def process_action(self):
        if self.file_or_dir == 'dir':
            self.messages.append('Cannot unzip a directory')
        else:
            try:
                self.path = os.path.normpath(self.path)  # strip trailing slash if any
                filename = (
                        self.config['basepath']
                        + self.current_path
                        + os.path.basename(self.path)
                )
                zip_ref = zipfile.ZipFile(filename, 'r')
                directory = self.config['basepath'] + self.current_path
                for file in zip_ref.namelist():
                    if file.endswith(tuple(self.config['extensions'])):
                        zip_ref.extract(file, directory)
                        mimetype = magic.from_file(directory + file, mime=True)
                        print(directory + file)
                        guessed_exts = mimetypes.guess_all_extensions(mimetype)
                        guessed_exts = [ext[1:] for ext in guessed_exts]
                        common = [ext for ext in guessed_exts if ext in self.config['extensions']]
                        if not common:
                            os.remove(directory + file)
                            self.messages.append(
                                "File in the zip is not allowed : "
                                + file
                            )
                zip_ref.close()
            except Exception as e:
                print(e)
                self.messages.append('ERROR : Could not unzip the file.')
            if len(self.messages) == 0:
                self.messages.append('Extraction completed successfully.')

        return self.messages


def handle_action(action, path, name, file_or_dir, files, current_path, messages, config):
    action_classes = {
        'upload': UploadAction,
        'add': AddAction,
        'delete': DeleteAction,
        'rename': RenameAction,
        'move': MoveAction,
        'copy': CopyAction,
        'unzip': UnzipAction,
    }

    action_class = action_classes.get(action)
    action_class_instance = action_class(action, path, name, file_or_dir, files, current_path, messages, config)
    new_messages = action_class_instance.process_action()

    return new_messages
