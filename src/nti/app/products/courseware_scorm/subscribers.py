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

from nti.app.products.courseware.interfaces import IAllCoursesCollection
from nti.app.products.courseware.interfaces import IAllCoursesCollectionAcceptsProvider

from nti.app.products.courseware_scorm.courses import SCORM_COURSE_MIME_TYPE

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

logger = __import__('logging').getLogger(__name__)


@component.adapter(IAllCoursesCollection)
@interface.implementer(IAllCoursesCollectionAcceptsProvider)
class SCORMAllCoursesCollectionAcceptsProvider(object):

    def __init__(self, courses_collection):
        self.courses_collection = courses_collection

    def __iter__(self):
        if component.queryUtility(ISCORMCloudClient) is not None:
            return iter([SCORM_COURSE_MIME_TYPE])
        return iter(())
