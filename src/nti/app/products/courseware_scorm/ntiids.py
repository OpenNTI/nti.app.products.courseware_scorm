#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import


from nti.app.contenttypes.presentation.ntiids import PresentationResolver

from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef

logger = __import__('logging').getLogger(__name__)


class _SCORMContentRefResolver(PresentationResolver):
    _ext_iface = ISCORMContentRef

