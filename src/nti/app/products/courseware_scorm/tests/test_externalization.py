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
        assert_that(ext_reg['app_id'], is_('appId'))
        assert_that(ext_reg['registration_id'], is_('regId'))
        assert_that(ext_reg['course_id'], is_('courseId'))
        assert_that(ext_reg['course_title'], is_('Title'))
        assert_that(ext_reg['last_course_version_launched'], is_('lastVersion'))
        assert_that(ext_reg['learner_id'], is_('learnerId'))
        assert_that(ext_reg['learner_first_name'], is_('learnerFirst'))
        assert_that(ext_reg['learner_last_name'], is_('learnerLast'))
        assert_that(ext_reg['email'], is_('email'))
        assert_that(ext_reg['create_date'], is_('createDate'))
        assert_that(ext_reg['first_access_date'], is_('firstAccess'))
        assert_that(ext_reg['last_access_date'], is_('lastAccess'))
        assert_that(ext_reg['completed_date'], is_('completedDate'))
        ext_inst = ext_reg['instances'][0]
        assert_that(ext_inst, is_not(none()))
        assert_that(ext_inst['instance_id'], is_('instanceId'))
        assert_that(ext_inst['course_version'], is_('version'))
        assert_that(ext_inst['update_date'], is_('updateDate'))
