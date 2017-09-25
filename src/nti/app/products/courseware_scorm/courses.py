#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from zope import interface

from nti.contenttypes.courses.courses import CourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata


@interface.implementer(ISCORMCourseInstance)
class SCORMCourseInstance(CourseInstance):
    """
    An instance of a SCORM course.
    """
    pass


@interface.implementer(IScormCourseMetadata)
class SCORMCourseMetadata(object):
    """
    A metadata object for a SCORM course instance.
    """
    pass
