#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from persistent import Persistent

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from zope.container.contained import Contained

from zope.intid.interfaces import IIntIds

from nti.app.products.courseware_scorm.interfaces import IScormIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.contenttypes.courses.courses import CourseInstance

from nti.contenttypes.courses.interfaces import ICourseInstance

SCORM_COURSE_METADATA_KEY = 'nti.app.produts.courseware_scorm.courses.metadata'

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISCORMCourseInstance)
class SCORMCourseInstance(CourseInstance):
    """
    An instance of a SCORM course.
    """


@component.adapter(ISCORMCourseInstance)
@interface.implementer(ISCORMCourseMetadata)
class SCORMCourseMetadata(Persistent, Contained):
    """
    A metadata object for a SCORM course instance.
    """
SCORMCourseInstanceMetadataFactory = an_factory(SCORMCourseMetadata,
                                                SCORM_COURSE_METADATA_KEY)


@component.adapter(ICourseInstance)
@interface.implementer(IScormIdentifier)
class ScormIdentifier(object):

    def __init__(self, course):
        self.course = course

    def get_id(self):
        # NTIIDs contain characters invalid for SCORM IDs, so use IntId
        intids = component.getUtility(IIntIds)
        return intids.queryId(self.course)
