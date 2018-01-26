#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import assert_that

from nti.app.products.courseware_scorm.interfaces import IScormInstance
from nti.app.products.courseware_scorm.interfaces import IScormRegistration

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.externalization.externalization import to_external_object

from nti.scorm_cloud.client.registration import Instance
from nti.scorm_cloud.client.registration import Registration


class TestExternal(ApplicationLayerTest):

    def test_scorm_registration(self):
        mock_instance = Instance(instanceId='instanceId', courseVersion='version', updateDate='updateDate')
        mock_reg = Registration(appId='appId', registrationId='regId', courseId='courseId',
                     courseTitle='Title', lastCourseVersionLaunched='lastVersion',
                     learnerId='learnerId', learnerFirstName='learnerFirst', learnerLastName='learnerLast',
                     email='email', createDate='createDate', firstAccessDate='firstAccess', lastAccessDate='lastAccess',
                     completedDate='completedDate', instances=[mock_instance])
        reg = IScormRegistration(mock_reg)
        assert_that(reg, is_not(none()))
        ext_reg = to_external_object(reg)
        assert_that(ext_reg, is_not(none()))
