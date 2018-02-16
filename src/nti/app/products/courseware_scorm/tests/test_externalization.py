#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries

from nti.app.products.courseware_scorm.interfaces import ISCORMProgress
from nti.app.products.courseware_scorm.interfaces import IScormRegistration

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.externalization.testing import externalizes

from nti.scorm_cloud.client.registration import Instance
from nti.scorm_cloud.client.registration import Registration
from nti.scorm_cloud.client.registration import RegistrationReport


class TestExternal(ApplicationLayerTest):

    def test_scorm_progress(self):
        report = RegistrationReport(format_=u'course',
                                    complete=u'incomplete',
                                    success=u'failure',
                                    totaltime=3,
                                    score=u'unknown')
        progress = ISCORMProgress(report, None)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    externalizes(has_entries(u'complete', u'incomplete',
                                             u'success', u'failure',
                                             u'total_time', 3,
                                             u'score', -1)))
        report.score=None
        progress = ISCORMProgress(report, None)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    externalizes(has_entries(u'complete', u'incomplete',
                                             u'success', u'failure',
                                             u'total_time', 3,
                                             u'score', -1)))
        report.score=u'100'
        progress = ISCORMProgress(report, None)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    externalizes(has_entries(u'complete', u'incomplete',
                                             u'success', u'failure',
                                             u'total_time', 3,
                                             u'score', 100)))


    def test_scorm_registration(self):
        mock_instance = Instance(instanceId='instanceId',
                                 courseVersion='version',
                                 updateDate='updateDate')
        mock_reg = Registration(appId='appId', registrationId='regId', courseId='courseId',
                                courseTitle='Title', lastCourseVersionLaunched='lastVersion',
                                learnerId='learnerId', learnerFirstName='learnerFirst',
                                learnerLastName='learnerLast', email='email',
                                createDate='createDate', firstAccessDate='firstAccess',
                                lastAccessDate='lastAccess', completedDate='completedDate',
                                instances=[mock_instance])
        reg = IScormRegistration(mock_reg, None)
        assert_that(reg, is_not(none()))
        assert_that(reg,
                    externalizes(has_entries('app_id', 'appId',
                                             'registration_id', 'regId',
                                             'course_id', 'courseId',
                                             'last_course_version_launched', 'lastVersion',
                                             'learner_id', 'learnerId',
                                             'learner_first_name', 'learnerFirst',
                                             'learner_last_name', 'learnerLast',
                                             'email', 'email',
                                             'create_date', 'createDate',
                                             'first_access_date', 'firstAccess',
                                             'last_access_date', 'lastAccess',
                                             'completed_date', 'completedDate',
                                             'instances', has_length(1),
                                             'instances', has_item(has_entries('instance_id', 'instanceId',
                                                                               'course_version', 'version',
                                                                               'update_date', 'updateDate')))))
