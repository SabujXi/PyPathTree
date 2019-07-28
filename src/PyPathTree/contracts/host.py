from abc import ABCMeta, abstractmethod


class HostContract(metaclass=ABCMeta):
    """Synamic and Site are hosts currently"""
    @property
    @abstractmethod
    def root_path(self):
        pass

    @property
    @abstractmethod
    def path_tree(self):
        pass

    @property
    @abstractmethod
    def data(self):
        pass

    @property
    def abs_root_path(self):
        # deprecated
        return self.root_path

    @property
    def default_data(self):
        # deprecated
        return self.data
