import re
from collections import deque

regex_type = type(re.compile(""))


class _CPath:
    """
    CPath => Content Path
    Convention:
    1. Content Path will be indicated as cpath
    2. String Path will be indicated as path
    """

    def __init__(self, path_tree, site, cpath_special_comps, is_file=True):
        self.__path_tree = path_tree
        self.__cpath_special_comps = cpath_special_comps
        self.__site = site
        self.__is_file = is_file
        if is_file:
            assert cpath_special_comps[-1] != ''
        else:
            assert cpath_special_comps[-1] == ''

        # make path comps
        comps = self.__cpath_special_comps
        # remove empty string from both ends
        if len(comps) > 1 and comps[-1] == '':
            comps = comps[:-1]
        if len(comps) > 1 and comps[0] == '':
            comps = comps[1:]

        self.__path_comps = comps

    @property
    def site(self):
        return self.__site

    @property
    def parent_cpath(self):
        path_comps = self.path_comps
        if len(path_comps) <= 1:
            # contents/a-file
            # contents/dirA/b-file
            # * contents cannot have parent (==None) (Content Path is not for the site root or above dirs! SO -_-)
            # TODO: content should have prent with empty comps ()? If I put < 1 then app will stuck in infinite loop
            # Fix it.
            return None
        new_comps = path_comps[:-1]
        pp = self.__path_tree.create_cpath(new_comps, is_file=False)
        assert pp.is_dir, "Logical error, inform the developer (Sabuj)"  # Just to be safe from future bug.
        return pp

    @property
    def parent_cpaths(self) -> tuple:
        parent_paths = deque()
        pp = self.parent_cpath
        while pp is not None:
            parent_paths.appendleft(pp)
            pp = pp.parent_cpath

        return tuple(parent_paths)

    @property
    def relative_path(self):
        """
        Relative paths are relative from site root.
        """
        return self.__path_tree.join_comps(*self.__cpath_special_comps).replace('\\', '/')

    @property
    def path_comps(self):
        return tuple(self.__path_comps)

    @property
    def path_comps_w_site(self):
        return (*self.__site.id.components, *self.__path_comps[1:])

    @property
    def cpath_comps(self):
        """Special cpath comps that can have '' empty string on both ends - path tree's to components make this
        special components"""
        return tuple(self.__cpath_special_comps)

    @property
    def abs_path(self):
        return self.__path_tree.get_full_path(self.__cpath_special_comps)

    @property
    def is_file(self):
        return self.__is_file

    @property
    def is_dir(self):
        return not self.__is_file

    @property
    def basename(self):
        """
        Relative base name
        """
        return self.path_comps[-1]

    @property
    def basename_wo_ext(self):
        if self.is_file:
            base, dot, ext = self.basename.rpartition('.')
            if dot == '':
                base = ext
                ext = ''
        else:
            base = self.basename
        return base

    @property
    def dirname_comps(self):
        """
        Relative dirname
        """
        return self.__cpath_special_comps[:-1]

    @property
    def extension(self, dot_count=1):
        if self.is_file:
            dotted_parts = self.basename.rsplit(".", maxsplit=dot_count)
            if not len(dotted_parts) < dot_count + 1:
                ext = ".".join(dotted_parts[-dot_count:])
                return ext
        return ''

    def list_cpaths(self, files_only=None, directories_only=None, depth=None, exclude_compss=(), checker=None,
                    respect_settings=True):
        return self.__path_tree.list_cpaths(
            files_only=files_only,
            directories_only=directories_only,
            initial_path_comps=self,
            depth=depth,
            exclude_compss=exclude_compss,
            checker=checker,
            respect_settings=respect_settings
        )

    def list_files(self, depth=None, exclude_compss=(), checker=None, respect_settings=True):
        _, cfiles = self.list_cpaths(files_only=True, depth=depth, exclude_compss=exclude_compss, checker=checker,
                                     respect_settings=respect_settings)
        return cfiles

    def list_dirs(self, depth=None, exclude_compss=(), checker=None, respect_settings=True):
        dirs, _ = self.list_cpaths(directories_only=True, depth=depth, exclude_compss=exclude_compss, checker=checker,
                                   respect_settings=respect_settings)
        return dirs

    def exists(self):
        """Real time checking"""
        return self.__path_tree.exists(self.__cpath_special_comps)

    def open(self, mode, *args, **kwargs):
        assert self.is_file, 'Cannot call open() on a directory: %s' % self.relative_path
        return self.__path_tree.open(self.__cpath_special_comps, mode, *args, **kwargs)

    def makedirs(self):
        assert self.is_dir
        return self.__path_tree.fs.makedirs(self.abs_path)

    def write_text(self, text):
        assert isinstance(text, str)
        assert self.is_file
        with self.open('w', encoding='utf-8') as fw:
            fw.write(text)

    def write_bytes(self, data):
        isinstance(data, (bytes, bytearray))
        assert isinstance(data, str)
        assert self.is_file
        with self.open('wb') as fw:
            fw.write(data)

    def write_stream(self, stream, close_on_done=False):
        assert hasattr(stream, 'read')
        assert self.is_file
        with self.open('wb') as fw:
            data = stream.read(1024)
            while data:
                fw.write(data)
                data = stream.read(1024)
        if close_on_done:
            stream.close()

    def write_text_stream(self, stream, close_on_done=False):
        assert hasattr(stream, 'read')
        assert self.is_file
        with self.open('w', encoding='utf-8') as fw:
            data = stream.read(1024)
            while data:
                fw.write(data)
                data = stream.read(1024)
        if close_on_done:
            stream.close()

    def make_file(self):
        assert self.is_file
        with self.open('wb') as fw:
            pass

    def join(self, *path_str_or_cmps, is_file=True, forgiving=False):
        """Creates a new path joining to this one"""
        comps = self.__path_tree.to_cpath_ccomps(
            *path_str_or_cmps)  # [p for p in re.split(r'[\\/]+', path_str) if p != '']
        if self.is_dir:
            new_path_comps = (*self.path_comps, *comps)
        else:
            new_path_comps = (*self.path_comps[:-1], self.path_comps[-1] + comps[0], *comps[1:])
        return self.__path_tree.create_cpath(new_path_comps, is_file=is_file, forgiving=forgiving)

    def join_as_cfile(self, *path_str_or_cmps, forgiving=False):
        return self.join(*path_str_or_cmps, is_file=True, forgiving=forgiving)

    def join_as_cdir(self, *path_str_or_cmps, forgiving=False):
        return self.join(*path_str_or_cmps, is_file=False, forgiving=forgiving)

    @staticmethod
    def __process_regex(regex, ignorecase=True):
        """Matches against relative path"""
        if isinstance(regex, str):
            if ignorecase:
                regex = re.compile(regex, re.IGNORECASE)
            else:
                regex = re.compile(regex, re.IGNORECASE)
        else:
            assert type(regex) is regex_type, "regex argument must provide compiled regular expression or string"
        return regex

    def match(self, regex, ignorecase=True):
        """Matches against relative path"""
        regex = self.__process_regex(regex, ignorecase)
        return regex.match(self.relative_path)

    def match_basename(self, regex, ignorecase=True):
        """"""
        regex = self.__process_regex(regex, ignorecase)
        return regex.match(self.basename)

    def match_extension(self, regex, ignorecase=True):
        """"""
        regex = self.__process_regex(regex, ignorecase)
        return regex.match(self.extension)

    def startswith(self, *comps):
        ccomps = self.__path_tree.to_cpath_ccomps(comps)
        if not (len(self.path_comps) < len(ccomps)):
            if self.path_comps[:len(ccomps)] == ccomps:
                return True
        return False

    def endswith(self, *comps):
        ccomps = self.__path_tree.to_cpath_ccomps(comps)
        if not (len(self.path_comps) < len(ccomps)):
            if self.path_comps[-len(ccomps):] == ccomps:
                return True
        return False

    def getmtime(self):
        return self.__path_tree.fs.getmtime(self.abs_path)

    def getctime(self):
        return self.__path_tree.fs.getctime(self.abs_path)

    @property
    def id(self):
        return '/'.join(self.path_comps)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.path_comps == other.path_comps and self.is_file == other.is_file

    def __hash__(self):
        return hash(self.path_comps)

    def __str__(self):
        return f"CPath: {self.relative_path}"

    def __repr__(self):
        return repr(str(self))
