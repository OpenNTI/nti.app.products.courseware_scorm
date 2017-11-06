#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest


class TestCourses(CoursewareSCORMLayerTest):

    def test_scorm_course_metadata(self):
        course_instance = SCORMCourseInstance()
        meta = ISCORMCourseMetadata(course_instance, None)
        assert_that(meta, is_not(none()))
