#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from nti.contenttypes.courses.courses import CourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance


@interface.implementer(ISCORMCourseInstance)
class SCORMCourseInstance(CourseInstance):
    """
    An instance of a SCORM course.
    """
    pass
