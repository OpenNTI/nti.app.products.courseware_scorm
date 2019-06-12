#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import none
from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IRegistrationReportContainer

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest


class TestCourses(CoursewareSCORMLayerTest):

    def test_scorm_course_metadata(self):
        course_instance = SCORMCourseInstance()
        meta = ISCORMCourseMetadata(course_instance, None)
        assert_that(meta, is_not(none()))
        assert_that(meta.has_scorm_package(), is_(False))
        meta.scorm_id = u'12345678'
        assert_that(meta.has_scorm_package(), is_(True))

        container = IRegistrationReportContainer(course_instance, None)
        assert_that(container, is_not(none()))

    def test_scorm_identifier(self):
        course_instance = SCORMCourseInstance()
        scorm_id = ISCORMIdentifier(course_instance)
        assert_that(scorm_id, is_not(none()))
