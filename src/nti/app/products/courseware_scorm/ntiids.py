#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.contenttypes.presentation.ntiids import PresentationResolver

from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo

from nti.ntiids.interfaces import INTIIDResolver

logger = __import__('logging').getLogger(__name__)


class _SCORMContentRefResolver(PresentationResolver):
    _ext_iface = ISCORMContentRef


@interface.implementer(INTIIDResolver)
class _ScormContentInfoResolver(object):

    _ext_iface = ISCORMContentInfo

    def resolve(self, key):
        result = component.queryUtility(self._ext_iface, name=key)
        return result
