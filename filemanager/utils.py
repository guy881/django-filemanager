import os


def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def rename_if_exists(folder, file):
    if folder[-1] != os.sep:
        folder = folder + os.sep
    if os.path.exists(folder + file):
        if file.find('.') == -1:
            # no extension
            for i in range(1000):
                if not os.path.exists(folder + file + '.' + str(i)):
                    break
            return file + '.' + str(i)
        else:
            extension = file[file.rfind('.'):]
            name = file[:file.rfind('.')]
            for i in range(1000):
                full_path = folder + name + '.' + str(i) + extension
                if not os.path.exists(full_path):
                    break
            return name + '.' + str(i) + extension
    else:
        return file
