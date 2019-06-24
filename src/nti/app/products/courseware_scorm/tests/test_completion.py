#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import not_none
from hamcrest import has_entries
from hamcrest import assert_that

from zope import component

from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfoContainer

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.app.products.courseware_scorm.model import ScormContentInfo

from nti.contenttypes.completion.interfaces import ICompletableItemCompletionPolicy

from nti.contenttypes.courses.courses import ContentCourseInstance

from nti.externalization.externalization import to_external_object


class TestSCORMCompletionPolicy(CoursewareSCORMLayerTest):

    def test_completion(self):
        course = ContentCourseInstance()
        content_info = ScormContentInfo(scorm_id=u'scorm_id')
        container = ISCORMContentInfoContainer(course, None)
        assert_that(container, not_none())
        container.store_content(content_info)
        policy = component.queryMultiAdapter((content_info, course),
                                             ICompletableItemCompletionPolicy)
        assert_that(policy, not_none())
        assert_that(to_external_object(policy), has_entries({'Class': 'SCORMCompletionPolicy',
                                                             'offers_completion_certificate': False}))
