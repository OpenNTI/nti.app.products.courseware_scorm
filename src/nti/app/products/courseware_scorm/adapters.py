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

from nti.app.products.courseware_scorm.interfaces import ISCORMContent
from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef

from nti.ntiids.ntiids import find_object_with_ntiid


@interface.implementer(ISCORMContent)
@component.adapter(ISCORMContentRef)
def _scormref_to_scormcontent(context):
    return find_object_with_ntiid(context.target or '')
