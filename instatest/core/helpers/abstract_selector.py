from instatest.core import InstatestObject


class AbstractSelector(InstatestObject):
    element_search_function = None

    def __init__(self, by, val):
        self._by = by
        self._val = val

    @property
    def by(self):
        return self._by

    @property
    def value(self):
        return self._val

    def get_value(self):
        return self._val

    def __str__(self):
        return self.to_string()

    def to_string(self):
        return "{0}={1}".format(self._by, self._val)
