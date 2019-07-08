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

from nti.app.products.courseware_scorm.interfaces import IScormContent
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISCORMContentInfo)
@component.adapter(IScormContent)
def _scormref_to_scormcontent(context):
    return find_object_with_ntiid(context.target or '')


@interface.implementer(ICourseInstance)
@component.adapter(ISCORMContentInfo)
def _scormcontent_to_course(context):
    # Strict false for tests
    return find_interface(context, ICourseInstance, strict=False)
