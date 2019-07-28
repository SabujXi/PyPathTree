"""
    author: "Md. Sabuj Sarker"
    copyright: "Copyright 2017-2019, The PyPathTree Project"
    credits: ["Md. Sabuj Sarker"]
    license: "MIT"
    maintainer: "Md. Sabuj Sarker"
    email: "md.sabuj.sarker@gmail.com"
    status: "Development"
"""
import re
from collections import deque
from PyPathTree.contracts.fs_backend import BaseFsBackendContract
from .backends import FileSystemBackend
from PyPathTree.contracts.host import HostContract
from PyPathTree.simple_host import SimpleHost

from PyPathTree.exceptions import InvalidCPathComponentError
from PyPathTree._cpath import _CPath

regex_type = type(re.compile(""))


def loaded(f):
    def method_wrapper(self, *args, **kwargs):
        assert self.is_loaded, "Class object of the method `%s`'s must be loaded before this method can be called" % f.__qualname__
        return f(self, *args, **kwargs)
    return method_wrapper


def not_loaded(f):
    def method_wrapper(self, *args, **kwargs):
        assert not self.is_loaded, "Must NOT be loaded before this method can be called"
        return f(self, *args, **kwargs)
    return method_wrapper


class _Patterns:
    path_sep = re.compile(r'[\\/]+')


class PathTree(object):
    def __init__(self, host_or_root):
        if isinstance(host_or_root, str):
            host = SimpleHost(host_or_root, self)
        else:
            host = host_or_root

        assert isinstance(host, HostContract)
        self.__host = host
        # TODO: assert os.path.isdir(host.site_root), "FileTree.__init__: _root must be a directory, `%s`"
        #  % host.site_root

        # default backend system
        self.__fs = FileSystemBackend()
        self.__is_loaded = False

    @property
    def host(self):
        return self.__host

    @property
    def fs(self):
        return self.__fs

    @property
    def is_loaded(self):
        return self.__is_loaded

    @not_loaded
    def load(self):
        self.__is_loaded = True

    @classmethod
    def __str_path_to_comps(cls, path_str):
        # converting sting paths like ('x', 'a/b\\path_comp_str') to ('x', 'a', 'b', 'path_comp_str')
        # assert path_str.strip() != ''  # by empty path we mean site root
        str_comps = []
        for path_comp_str in _Patterns.path_sep.split(path_str):
            path_comp_str = path_comp_str.strip()
            str_comps.append(path_comp_str)
        return str_comps

    @classmethod
    def __sequence_path_to_comps(cls, path_sequence):
        str_comps = []
        for path_comp in path_sequence:
            if isinstance(path_comp, str):
                str_comps.extend(cls.__str_path_to_comps(path_comp))
            elif isinstance(path_comp, (list, tuple)):
                str_comps.extend(cls.__sequence_path_to_comps(path_comp))
            else:
                raise InvalidCPathComponentError(
                    f'Invalid component type for path: {type(path_comp)} whose value is {path_comp}'
                )

        return str_comps

    @classmethod
    def to_cpath_ccomps(cls, *path_comps):
        """Creates special cpath components that can have '' empty string on both ends
        To get components (without empty string on both ends) use path_comps property on cpath object"""
        comps = []
        for path_comp in path_comps:
            if isinstance(path_comp, str):
                comps.extend(cls.__str_path_to_comps(path_comp))
            elif isinstance(path_comp, (tuple, list)):
                comps.extend(cls.__sequence_path_to_comps(path_comp))
            elif type(path_comp) is _CPath:
                # TODO: should check that called and caller are in the same site. This method is clcass method
                # and i cannot check the validity now.
                comps.extend(path_comp.path_comps)
            else:
                raise InvalidCPathComponentError(
                    f"Path comps must be list, tuple, string or _CPath object when it is not string: {type(path_comp)}"
                    f" where value is {path_comp}"
                )

        # remove empty '' part except for the first and last one
        _ = []
        for idx, comp in enumerate(comps):
            if idx in {0, len(comps) - 1}:
                # keep empty string for first and last part
                _.append(comp)
            else:
                # ignore the empty string.
                if comp != '':
                    _.append(comp)
        comps = _

        # Relative URL processing.
        _ = []
        for idx, comp in enumerate(comps):
            if comp == '..':
                if idx > 0:
                    del _[-1]
            elif comp == '.':
                # skip
                continue
            else:
                _.append(comp)
        else:
            if _ == []:
                _ = ['']
            if _[0] != '':
                _.insert(0, '')
        comps = _

        return tuple(comps)

    @classmethod
    def to_path_comps(cls, *path_comps):
        """The one returned by CPath.path_comps"""
        ccomps = cls.to_cpath_ccomps(*path_comps)
        # remove empty string from both ends
        if len(ccomps) > 1 and ccomps[-1] == '':
            ccomps = ccomps[:-1]
        if len(ccomps) > 1 and ccomps[0] == '':
            ccomps = ccomps[1:]

        comps = ccomps
        return comps

    def create_cpath(self, *path_comps, is_file=False, forgiving=False):
        """
        Create a Content Path object.
        :forgiving: if forgiving is True then it will not consider a result of path component ending in '' to be error.
            This method is only for end user who do not know deep details or for from template or when you want a relaxed
            way of doing things * Must not use in synamic core development.*
        """
        ccomps = self.to_cpath_ccomps(*path_comps)
        if not is_file:  # directory
            if ccomps[-1] != '':
                ccomps += ('', )
        else:  # file
            if not forgiving:  # is file & not forgiving
                assert ccomps[-1] != '', f'Invalid ccomps[-1] -> ccomps: {ccomps}'
            else:  # is file & forgiving.
                if len(ccomps) > 1 and ccomps[-1] == '':
                    ccomps = ccomps[:-1]

        path_obj = _CPath(self, self.__host, ccomps, is_file=is_file)
        return path_obj

    def create_file_cpath(self, *path_comps, forgiving=False):
        return self.create_cpath(*path_comps, is_file=True, forgiving=forgiving)

    def create_dir_cpath(self, *path_comps, forgiving=False):
        return self.create_cpath(*path_comps, is_file=False, forgiving=forgiving)

    def exists(self, *path) -> bool:
        comps = self.to_cpath_ccomps(*path)
        """Checks existence relative to the root"""
        return True if self.__fs.exists(self.__full_path__(comps)) else False

    def is_file(self, *path) -> bool:
        comps = self.to_cpath_ccomps(*path)
        fn = self.__full_path__(comps)
        return True if self.__fs.is_file(fn) else False

    def is_dir(self, *path) -> bool:
        comps = self.to_cpath_ccomps(*path)
        fn = self.__full_path__(comps)
        return True if self.__fs.is_dir(fn) else False

    def join(self, *content_paths, is_file=False, forgiving=False):
        comps = self.to_cpath_ccomps(*content_paths)
        return self.create_cpath(comps, is_file=is_file, forgiving=forgiving)

    def open(self, file_path, *args, **kwargs):
        comps = self.to_cpath_ccomps(file_path)
        fn = self.__full_path__(comps)
        return open(fn, *args, **kwargs)

    def makedirs(self, *dir_path):
        comps = self.to_cpath_ccomps(*dir_path)
        full_p = self.__full_path__(comps)
        self.__fs.makedirs(full_p)

    @staticmethod
    def join_comps(*comps):
        """Comps must be strings
        Replacement for os path join as that discards empty string instead of putting a forward slash there"""
        _ = []
        for idx, comp in enumerate(comps):
            assert isinstance(comp, str), f'Provided type {type(comp)}'
            while comp.endswith(('/', '\\')):
                comp = comp[:-1]
            if idx > 0:
                while comp.startswith(('/', '\\')):
                    comp = comp[1:]

            if idx not in (0, len(comps) - 1):
                if comp == '':
                    # ignore empty string to avoid double slash in path
                    continue
            _.append(comp)
        return '/'.join(_)

    def get_full_path(self, *comps) -> str:
        comps = self.to_cpath_ccomps(*comps)
        return self.join_comps(self.__host.abs_root_path, *comps)

    def __full_path__(self, comps):
        # for internal use only where there is no normalization needed with self.to_cpath_comps
        """Comma separated arguments of path components or os.sep separated paths"""
        return self.join_comps(self.__host.abs_root_path, *comps)

    def __list_cpaths_loop2(self, starting_comps=(), files_only=None, directories_only=None, depth=None, exclude_cpaths=(), checker=None, respect_settings=True):
        return self.__ListCPathsLoop(
            self,
            starting_comps=starting_comps,
            files_only=files_only,
            directories_only=directories_only,
            depth=depth,
            exclude_cpaths=exclude_cpaths,
            checker=checker,
            respect_settings=respect_settings)()

    def list_cpaths(self, initial_path_comps=(), files_only=None, directories_only=None, depth=None, exclude_compss=(), checker=None, respect_settings=True):
        if type(initial_path_comps) is _CPath:
            assert initial_path_comps.is_dir
            starting_comps = initial_path_comps.path_comps
        else:
            starting_comps = self.to_cpath_ccomps(initial_path_comps)
        _exclude_compss = []
        for pc in exclude_compss:
            _exclude_compss.append(self.to_cpath_ccomps(pc))
        exclude_compss = tuple(_exclude_compss)

        dirs, files = self.__list_cpaths_loop2(starting_comps, files_only=files_only, directories_only=directories_only, depth=depth, exclude_cpaths=exclude_compss, checker=checker, respect_settings=respect_settings)
        return dirs, files

    def list_file_cpaths(self, initial_path_comps=(), depth=None, exclude_compss=(), checker=None, respect_settings=True):
        _, files = self.list_cpaths(initial_path_comps, files_only=True, depth=depth, exclude_compss=exclude_compss, checker=checker, respect_settings=respect_settings)
        return files

    def list_dir_cpaths(self, initial_path_comps='', depth=None, exclude_compss=(), checker=None, respect_settings=True):
        dirs, _ = self.list_cpaths(initial_path_comps, directories_only=True, depth=depth, exclude_compss=exclude_compss, checker=checker, respect_settings=respect_settings)
        return dirs

    def is_type_cpath(self, other):
        return type(other) is _CPath

    def __set_fs__(self, fs_instance):
        assert isinstance(fs_instance, BaseFsBackendContract)
        self.__fs = fs_instance

    class __ListCPathsLoop:
        def __init__(self, path_tree, starting_comps=(), files_only=None, directories_only=None, depth=None, exclude_cpaths=None, checker=None, respect_settings=True):
            self.path_tree = path_tree
            self.starting_comps = None
            self.files_only = files_only
            self.directories_only = directories_only
            self.depth = depth
            self.exclude_cpaths = None
            self.checker = checker
            self.respect_settings = respect_settings

            if starting_comps is None:
                self.starting_comps = ()
            else:
                self.starting_comps = self.path_tree.to_path_comps(starting_comps)

            for exclude_comps in exclude_cpaths:
                assert type(exclude_comps) is tuple, f"exclude_cpaths must contain tuple of strings as path." \
                                                     f" {exclude_comps} found"

            # check that files only and directories only both are not set to the Truth value
            if files_only is True:
                assert directories_only is not True
            if directories_only is True:
                assert files_only is not True

            # depth
            assert isinstance(depth, (type(None), int)), f"Type of depth must be None or int, {type(depth)}" \
                                                             f" found with value {depth}"
            if depth is None:
                self.depth = 2147483647

            # exclude cpaths validation
            _ = set()
            if exclude_cpaths is None:
                exclude_cpaths = set()
            for exclude_cpath in exclude_cpaths:
                assert self.path_tree.is_type_cpath(exclude_cpath)
                _.add(exclude_cpath)
            else:
                self.exclude_cpaths = _

            # default configs
            _dc = self.path_tree.host.system_settings['configs']
            self.__ignore_dirs_sw = tuple(_dc.get('ignore_dirs_sw', tuple()))
            self.__ignore_files_sw = tuple(_dc.get('ignore_files_sw', tuple()))

        def __call__(self, *args, **kwargs):
            """
                    A function to get all paths recursively starting from abs_root but returns a list of paths relative to the
                    .root
                    prefix_relative_root is fixed on every recursion
                    BUT next_relative_root isn't

                    exclude_comps_tuples: *components* list that are excluded from listing
                    checker: callables that accepts parameters: __ContentPath2 instance.
                    """
            absolute_root = self.path_tree.__full_path__(self.starting_comps)
            assert self.path_tree.fs.exists(absolute_root), f"Absolute root must exist: {absolute_root}"

            # new
            to_travel = deque([((*self.starting_comps, comp), 1) for comp in self.path_tree.fs.listdir(absolute_root)])
            directories = []
            files = []

            while len(to_travel) != 0:
                path_comps_n_depth = to_travel.popleft()
                path_comps = path_comps_n_depth[0]
                path_depth = path_comps_n_depth[1]
                if path_depth > self.depth:
                    break
                path_base = path_comps[-1]
                path_abs = self.path_tree.__full_path__(path_comps)

                if self.path_tree.fs.is_file(path_abs) and (self.files_only in (True, None)):
                    move_in = True
                    path_obj = self.path_tree.create_cpath(path_comps, is_file=True)
                    if self.checker is not None and not self.checker(path_obj):
                        move_in = False

                    elif self.respect_settings and path_base.startswith(self.__ignore_files_sw):
                        move_in = False

                    elif path_obj in self.exclude_cpaths:
                        move_in = False

                    if move_in:
                        files.append(path_obj)

                elif self.path_tree.fs.is_dir(path_abs) and (self.directories_only in (True, None)):
                    path_obj = self.path_tree.create_cpath(path_comps, is_file=False)
                    move_in = True
                    if self.checker is not None and not self.checker(path_obj):
                        move_in = False

                    elif self.respect_settings and path_base.startswith(self.__ignore_dirs_sw):
                        move_in = False

                    elif path_obj in self.exclude_cpaths:
                        move_in = False

                    if move_in:
                        directories.append(path_obj)
                        # Recurse
                        to_travel.extend(
                            tuple([((*path_comps, comp), path_depth + 1) for comp in self.path_tree.fs.listdir(path_abs)]))
                else:
                    raise Exception(f"ContentPath is neither dir, nor file: {path_abs}. Files only: {self.files_only} "
                                    f"Dirs only: {self.directories_only}. ")
            return directories, files

