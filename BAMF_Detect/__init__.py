from sys import path
import BAMF_Detect.modules
import BAMF_Detect.modules.common
from os.path import isfile, isdir, join, abspath, dirname, getsize
from pefile import PE
from glob import iglob
from zipfile import is_zipfile, ZipFile

path.append(dirname(abspath(__file__)))


def get_version():
    return "1.2.1"


def get_loaded_modules():
    l = []
    for m in modules.common.Modules.list:
        l.append(m.get_metadata())
    return l


def scan_file_data(file_content, module_filter, only_detect):
    """

    @param file_content:
    @param module_filter:
    @param only_detect:
    @return:
    """
    # todo consider modularized data preprocessors
    # todo php deobfuscation preprocessor
    is_pe = False
    try:
        PE(data=file_content)
        is_pe = True
        if modules.common.is_upx_compressed(file_content):
            replacement = modules.common.decompress_upx(file_content)
            if replacement is not None:
                file_content = replacement
    except KeyboardInterrupt:
        raise
    except:
        is_pe = False

    for m in modules.common.Modules.list:
        if not is_pe and m.get_datatype() == "PE":
            continue
        if module_filter is not None and m.get_module_name() not in module_filter:
            continue
        if m.is_bot(file_content):
            results = {}
            if not only_detect:
                results["information"] = m.get_bot_information(file_content)
            results["type"] = m.get_bot_name()
            results["module"] = m.get_module_name()
            results["description"] = m.get_metadata().description
            return results
    return None


def handle_file(file_path, module_filter, only_detect, is_temp_file=False):
    # todo add handling of archives
    if is_zipfile(file_path):
        # extract each file and handle it
        # todo Add archive password support
        try:
            z = ZipFile(file_path)
            for n in z.namelist():
                data = z.read(n)
                r = scan_file_data(data, module_filter, only_detect)
                if r is not None:
                    yield file_path + "," + n, r
        except KeyboardInterrupt:
            raise
        except:
            pass
    else:
        # assume we are dealing with a normal file
        # todo Convert file handling to use file paths
        if getsize(file_path) < 1024 * 1024 * 1024:
            with open(file_path, mode='rb') as file_handle:
                file_content = file_handle.read()
                r = scan_file_data(file_content, module_filter, only_detect)
                if r is not None:
                    yield file_path, r
    pass


def scan_paths(paths, only_detect, recursive, module_filter):
    """
    Scans paths for known bots and dumps information from them

    @rtype : dict
    @param paths: list of paths to check for files
    @param only_detect: only detect known bots, don't process configuration information
    @param recursive: recursively traverse folders
    @param module_filter: if not None, only modules in list will be used
    @return: dictionary of file to dictionary of information for each file
    """
    while len(paths) != 0:
        file_path = abspath(paths[0])
        del paths[0]
        if isfile(file_path):
            for fp, r in handle_file(file_path, module_filter, only_detect):
                yield fp, r
        elif isdir(file_path):
            for p in iglob(join(file_path, "*")):
                p = join(file_path, p)
                if isdir(p) and recursive:
                    paths.append(p)
                if isfile(p):
                    for fp, r in handle_file(p, module_filter, only_detect):
                        yield fp, r