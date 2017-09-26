#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from zope import component
from zope import interface
from zope.annotation.factory import factory as an_factory

from nti.contenttypes.courses.courses import CourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata


SCORM_COURSE_METADATA_KEY = 'nti.app.produts.courseware_scorm.courses.metadata'


@interface.implementer(ISCORMCourseInstance)
class SCORMCourseInstance(CourseInstance):
    """
    An instance of a SCORM course.
    """


@component.adapter(ISCORMCourseInstance)
@interface.implementer(ISCORMCourseMetadata)
class SCORMCourseMetadata(object):
    """
    A metadata object for a SCORM course instance.
    """

SCORMCourseInstanceMetadata = an_factory(SCORMCourseMetadata, SCORM_COURSE_METADATA_KEY)
