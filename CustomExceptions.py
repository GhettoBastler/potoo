#!/usr/bin/env python

import warnings


class SameNameError(Exception):
    """
    Raised if two files/directory have the same name
    """
    def __init__(self, name):
        self.msg = f'The name {name} already exists.'
        super().__init__(self.msg)


class UnknownLocalLinkWarning(Warning):
    def __init__(self, url):
        self.message = f'{url} cannot be resolved as an output file'

    def __str__(self):
        return repr(self.message)
