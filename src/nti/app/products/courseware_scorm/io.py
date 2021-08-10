#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.externalization.datastructures import InterfaceObjectIO

from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo

class ScormContentInfoIO(InterfaceObjectIO):

    __allowed_keys__ = frozenset({'tags'})

    _ext_iface_upper_bound = ISCORMContentInfo

    def _ext_accept_update_key(self, k, ext_self, ext_keys):
        return k in self.__allowed_keys__ \
            and InterfaceObjectIO._ext_accept_update_key(self, k, ext_self, ext_keys)
