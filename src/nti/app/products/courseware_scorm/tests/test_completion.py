#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entries
from hamcrest import assert_that

from zope import component

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.contenttypes.completion.interfaces import ICompletableItemCompletionPolicy

from nti.externalization.externalization import to_external_object

class TestSCORMCompletionPolicy(CoursewareSCORMLayerTest):

    def test_externalization(self):
        course = SCORMCourseInstance()
        metadata = ISCORMCourseMetadata(course)
        policy = component.queryMultiAdapter((metadata, course), ICompletableItemCompletionPolicy)
        assert_that(policy, is_not(none))
        assert_that(to_external_object(policy), has_entries({'Class': 'SCORMCompletionPolicy',
                                                             'offers_completion_certificate': False}))
