import os
from PyPathTree.contracts.host import HostContract


class SimpleHost(HostContract):
    def __init__(self, root_path, path_tree, data=None):
        assert os.path.exists(root_path)  # TODO: proper error message and exception
        assert os.path.isabs(root_path), f"Path {root_path} is not an absolute path, you must use absolute path"
        self.__root_path = root_path

        self.__path_tree = path_tree

        if data is None:
            data = {}
        self.__data = data

    @property
    def root_path(self):
        return self.__root_path

    @property
    def path_tree(self):
        return self.__path_tree

    @property
    def data(self):
        return self.__data
