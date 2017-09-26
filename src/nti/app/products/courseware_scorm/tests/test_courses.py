#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import is_not
from hamcrest import none
from hamcrest import assert_that

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance
from nti.app.products.courseware_scorm.courses import SCORMCourseMetadata
from nti.app.products.courseware_scorm.courses import SCORM_COURSE_METADATA_KEY

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

class TestCourses(CoursewareSCORMLayerTest):

    def test_scorm_course_metadata(self):
        course_instance = SCORMCourseInstance()
        assert_that(course_instance, is_not(none()))
        from IPython.terminal.debugger import set_trace;set_trace()
        meta = ISCORMCourseMetadata(course_instance)
        assert_that(meta, is_not(none()))
        # annotation = course_instance.__annotations__[SCORM_COURSE_METADATA_KEY]
        # assert_that(annotation, is_not(none()))
