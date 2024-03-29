#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import instance_of
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import contains_inanyorder

from datetime import datetime

from nti.app.products.courseware_scorm.interfaces import ISCORMRuntime
from nti.app.products.courseware_scorm.interfaces import ISCORMActivity
from nti.app.products.courseware_scorm.interfaces import ISCORMObjective
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo
from nti.app.products.courseware_scorm.interfaces import ISCORMInteraction
from nti.app.products.courseware_scorm.interfaces import IScormRegistration
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationReport

from nti.app.products.courseware_scorm.model import SCORMContentRef
from nti.app.products.courseware_scorm.model import ScormContentInfo

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.testing import externalizes

from nti.scorm_cloud.client.course import CourseData

from nti.scorm_cloud.client.registration import Static
from nti.scorm_cloud.client.registration import Comment
from nti.scorm_cloud.client.registration import Runtime
from nti.scorm_cloud.client.registration import Activity
from nti.scorm_cloud.client.registration import Instance
from nti.scorm_cloud.client.registration import Response
from nti.scorm_cloud.client.registration import Objective
from nti.scorm_cloud.client.registration import Interaction
from nti.scorm_cloud.client.registration import Registration
from nti.scorm_cloud.client.registration import LearnerPreference
from nti.scorm_cloud.client.registration import RegistrationReport

ID = StandardExternalFields.ID


class TestExternal(ApplicationLayerTest):

    def test_scorm_content(self):
        course_data = CourseData()
        course_data.title = u'new title'
        course_data.courseId = u'123456'
        course_data.numberOfVersions = u'2'
        course_data.numberOfRegistrations = u'18'
        course_data.learningStandard = u'aicc'
        content = ISCORMContentInfo(course_data)
        ext_obj = toExternalObject(content, decorate=False)
        assert_that(ext_obj, has_entries(u'title', u'new title',
                                         u'scorm_id', u'123456',
                                         u'course_version', u'2',
                                         u'registration_count', 18,
                                         u'learning_standard', 'aicc'))

        assert_that(find_factory_for(ext_obj),
                    not_none())

        # Bad data
        course_data.numberOfRegistrations = u'aaa'
        content = ISCORMContentInfo(course_data)
        ext_obj = toExternalObject(content, decorate=False)
        assert_that(ext_obj, has_entries(u'title', u'new title',
                                         u'scorm_id', u'123456',
                                         u'course_version', u'2',
                                         u'registration_count', none()))

    def test_scorm_content_info(self):
        content = ScormContentInfo(scorm_id=u'123456',
                                   title=u'scorm title',
                                   course_version=u'v1',
                                   registration_count=10,
                                   tags=[u'tag1', u'tag2'],
                                   learning_standard='cmi5')

        ext_obj = toExternalObject(content, decorate=False)
        assert_that(ext_obj, has_entries(u'scorm_id', u'123456',
                                         u'title', u'scorm title',
                                         u'course_version', u'v1',
                                         u'registration_count', 10,
                                         u'learning_standard', 'cmi5'))

        assert_that(find_factory_for(ext_obj),
                    not_none())

        internal = find_factory_for(ext_obj)(scorm_id=u'123456',
                                             title=u'scorm title',
                                             course_version=u'v1',
                                             registration_count=10,
                                             learning_standard='cmi5')
        internal.title = u'a title'
        assert_that(internal, instance_of(ScormContentInfo))
        assert_that(internal.title, is_(u'a title'))
        assert_that(internal.tags, is_(none()))

        # Only tags are actually updated
        update_from_external_object(internal,
                                    ext_obj,
                                    require_updater=True)
        assert_that(internal.title, is_(u'a title')) # wasn't overwritten
        assert_that(internal.tags, contains_inanyorder(u'tag1', u'tag2'))

    def test_scorm_content_ref(self):
        target = u'tag:nextthought.com,2011-10:NTI-3663246001124377908_4744212239739874217'
        ref = SCORMContentRef(target=target,
                              title=u'scorm content title',
                              description=u'scorm description')
        ext_obj = toExternalObject(ref)
        assert_that(ext_obj, has_entries(u'target', target,
                                         u'title', u'scorm content title',
                                         u'description', u'scorm description'))

        assert_that(find_factory_for(ext_obj),
                    not_none())

        internal = find_factory_for(ext_obj)()
        update_from_external_object(internal,
                                    ext_obj,
                                    require_updater=True)
        assert_that(internal.target, is_(target))
        assert_that(internal.title, is_(u'scorm content title'))
        assert_that(internal.description, is_(u'scorm description'))

    def test_scorm_progress(self):
        report = RegistrationReport(format_=u'course',
                                    regid=u'regid',
                                    instanceid=u'instanceid',
                                    complete=u'incomplete',
                                    success=u'failed',
                                    totaltime=3,
                                    score=u'unknown')
        progress = ISCORMRegistrationReport(report, None)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    externalizes(has_entries(u'format', u'course',
                                             u'registration_id', u'regid',
                                             u'instance_id', u'instanceid',
                                             u'complete', False,
                                             u'success', False,
                                             u'total_time', 3,
                                             u'score', None,
                                             u'activity', None)))
        report.format = u'activity'
        report.score = None
        report.success = u'unknown'
        progress = ISCORMRegistrationReport(report, None)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    externalizes(has_entries(u'format', u'activity',
                                             u'registration_id', u'regid',
                                             u'instance_id', u'instanceid',
                                             u'complete', False,
                                             u'success', True,
                                             u'total_time', 3,
                                             u'score', None,
                                             u'activity', None)))
        report.format = u'full'
        report.score=u'100'
        report.complete = u'complete'
        report.success = u'passed'
        report.activity = Activity(id_=u'a-id', title=u'activity-title')
        progress = ISCORMRegistrationReport(report, None)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    externalizes(has_entries(u'format', u'full',
                                             u'registration_id', u'regid',
                                             u'instance_id', u'instanceid',
                                             u'complete', True,
                                             u'success', True,
                                             u'total_time', 3,
                                             u'score', 100,
                                             u'activity', has_entries(ID, u'a-id',
                                                                      'title', u'activity-title',
                                                                      'complete', None,
                                                                      'success', True,
                                                                      'satisfied', False,
                                                                      'completed', False,
                                                                      'progress_status', False,
                                                                      'attempts', 1,
                                                                      'suspended', False,
                                                                      'time', None,
                                                                      'score', None,
                                                                      'objectives', [],
                                                                      'children', [],
                                                                      'runtime', None))))


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

    def test_scorm_objective(self):
        mock_objective = Objective(id_=u'id',
                                   measurestatus=True,
                                   normalizedmeasure=0.5,
                                   progressstatus=True,
                                   satisfiedstatus=True,
                                   score_scaled=u'1.0',
                                   score_min=u'0',
                                   score_raw=u'100',
                                   success_status=u'passed',
                                   completion_status=u'completed',
                                   progress_measure=u'1',
                                   description=u'description')
        objective = ISCORMObjective(mock_objective)
        assert_that(objective, is_not(none()))
        assert_that(objective,
                    externalizes(has_entries(ID, 'id',
                                             'measure_status', True,
                                             'normalized_measure', 0.5,
                                             'progress_status', True,
                                             'satisfied_status', True,
                                             'score_scaled', 1.0,
                                             'score_min', 0.0,
                                             'score_raw', 100.0,
                                             'success_status', True,
                                             'completion_status', u'completed',
                                             'progress_measure', 1.0,
                                             'description', u'description')))

    def test_scorm_interaction(self):
        mock_objective = Objective(id_=u'o-id')
        mock_response = Response(id_=u'r-id', value=u'r-value')
        mock_interaction = Interaction(id_=u'i-id',
                                       timestamp=u'0001:01:27.76',
                                       weighting=u'1.2',
                                       learner_response=mock_response,
                                       result=u'correct',
                                       latency=u'27.73',
                                       description=u'i-description',
                                       objectives=[mock_objective],
                                       correct_responses=[u'r-value'])
        interaction = ISCORMInteraction(mock_interaction)
        assert_that(interaction, is_not(none()))
        assert_that(interaction,
                    externalizes(has_entries(ID, 'i-id',
                                             'timestamp', 3687.76,
                                             'weighting', 1.2,
                                             'result', 'correct',
                                             'latency', 27.73,
                                             'description', 'i-description',
                                             'learner_response', has_entries(ID, u'r-id',
                                                                             'value', u'r-value'),
                                             'objectives', has_item(has_entries(ID, 'o-id',
                                                                                'measure_status', False,
                                                                                'normalized_measure', 0.0,
                                                                                'progress_status', False,
                                                                                'satisfied_status', False,
                                                                                'score_scaled', None,
                                                                                'score_min', None,
                                                                                'score_raw', None,
                                                                                'success_status', True,
                                                                                'completion_status', None,
                                                                                'progress_measure', None,
                                                                                'description', None)),
                                             'correct_responses', has_item(has_entries(ID, u'',
                                                                                       'value', u'r-value')))))

    def test_scorm_runtime(self):
        mock_static = Static(completion_threshold=u'0.5',
                             launch_data=u's-launch-data',
                             learner_id=u's-lid',
                             learner_name=u's-learner-name',
                             max_time_allowed=u'100',
                             scaled_passing_score=u'0.9',
                             time_limit_action=u'continue,message')
        mock_objective = Objective(id_=u'o-id')
        mock_interaction = Interaction(id_=u'i-id')
        mock_preference = LearnerPreference(audio_level=u'2.0',
                                            language=u'en',
                                            delivery_speed=u'1.0',
                                            audio_captioning=u'1')
        mock_comment = Comment(value=u'comment',
                               location=u'14',
                               date_time=u'20180321193726')
        mock_runtime = Runtime(completion_status=u'completed',
                               credit=u'credit',
                               entry=u'resume',
                               exit_=u'normal',
                               location=u'14',
                               mode=u'normal',
                               progress_measure=u'0.5',
                               score_scaled=u'0.5',
                               score_raw=u'80',
                               total_time=u'0000:00:27.63',
                               timetracked=u'0000:00:20.36',
                               success_status=u'unknown',
                               suspend_data=u'suspend-data',
                               learnerpreference=mock_preference,
                               static=mock_static,
                               comments_from_learner=[mock_comment],
                               comments_from_lms=[mock_comment],
                               interactions=[mock_interaction],
                               objectives=[mock_objective])
        runtime = ISCORMRuntime(mock_runtime)
        assert_that(runtime, is_not(none()))
        assert_that(runtime,
                    externalizes(has_entries('completion_status', u'completed',
                                             'credit', True,
                                             'entry', u'resume',
                                             'exit', u'normal',
                                             'location', u'14',
                                             'mode', u'normal',
                                             'progress_measure', 0.5,
                                             'score_scaled', 0.5,
                                             'score_raw', 80,
                                             'total_time', 27.63,
                                             'time_tracked', 20.36,
                                             'success_status', True,
                                             'suspend_data', u'suspend-data',
                                             'learner_preference', has_entries('audio_level', 2.0,
                                                                               'language', u'en',
                                                                               'delivery_speed', 1.0,
                                                                               'audio_captioning', u'1'),
                                             'static', has_entries('completion_threshold', 0.5,
                                                                   'launch_data', u's-launch-data',
                                                                   'learner_id', u's-lid',
                                                                   'learner_name', u's-learner-name',
                                                                   'max_time_allowed', 100,
                                                                   'scaled_passing_score', 0.9,
                                                                   'time_limit_action', u'continue,message'),
                                             'comments_from_learner', has_item(has_entries('value', u'comment',
                                                                                           'location', u'14',
                                                                                           'date_time', toExternalObject(
                                                                                                            datetime(2018, 3, 21, 19, 37, 26)))),
                                             'comments_from_lms', has_item(has_entries('value', u'comment',
                                                                                           'location', u'14',
                                                                                           'date_time', toExternalObject(
                                                                                                            datetime(2018, 3, 21, 19, 37, 26)))),
                                             'interactions', has_item(has_entries(ID, u'i-id',
                                                                                  'timestamp', None,
                                                                                  'weighting', None,
                                                                                  'learner_response', None,
                                                                                  'result', None,
                                                                                  'latency', None,
                                                                                  'description', None,
                                                                                  'objectives', [],
                                                                                  'correct_responses', None)),
                                             'objectives', has_item(has_entries(ID, 'o-id',
                                                                                'measure_status', False,
                                                                                'normalized_measure', 0.0,
                                                                                'progress_status', False,
                                                                                'satisfied_status', False,
                                                                                'score_scaled', None,
                                                                                'score_min', None,
                                                                                'score_raw', None,
                                                                                'success_status', True,
                                                                                'completion_status', None,
                                                                                'progress_measure', None,
                                                                                'description', None)))))

    def test_scorm_activity(self):
        mock_objective = Objective(id_=u'o-id')
        mock_child = Activity(id_=u'c-id', title=u'child-title')
        mock_runtime = Runtime()
        mock_activity = Activity(id_=u'a-id',
                                 title=u'activity-title',
                                 complete=u'complete',
                                 success=u'passed',
                                 satisfied=True,
                                 completed=True,
                                 progressstatus=True,
                                 attempts=2,
                                 suspended=True,
                                 time_=u'10',
                                 score=u'0.93',
                                 objectives=[mock_objective],
                                 children=[mock_child],
                                 runtime=mock_runtime)
        activity = ISCORMActivity(mock_activity)
        assert_that(activity, is_not(none()))
        assert_that(activity,
                    externalizes(has_entries(ID, u'a-id',
                                             'title', u'activity-title',
                                             'complete', True,
                                             'success', True,
                                             'satisfied', True,
                                             'completed', True,
                                             'progress_status', True,
                                             'attempts', 2,
                                             'suspended', True,
                                             'time', 10,
                                             'score', 0.93,
                                             'objectives', has_item(has_entries(ID, 'o-id',
                                                                                'measure_status', False,
                                                                                'normalized_measure', 0.0,
                                                                                'progress_status', False,
                                                                                'satisfied_status', False,
                                                                                'score_scaled', None,
                                                                                'score_min', None,
                                                                                'score_raw', None,
                                                                                'success_status', True,
                                                                                'completion_status', None,
                                                                                'progress_measure', None,
                                                                                'description', None)),
                                             'children', has_item(has_entries(ID, u'c-id',
                                                                              'title', u'child-title',
                                                                              'complete', None,
                                                                              'success', True,
                                                                              'satisfied', False,
                                                                              'completed', False,
                                                                              'progress_status', False,
                                                                              'attempts', 1,
                                                                              'suspended', False,
                                                                              'time', None,
                                                                              'score', None,
                                                                              'objectives', [],
                                                                              'children', [],
                                                                              'runtime', None)),
                                             'runtime', has_entries('completion_status', None,
                                                                    'credit', None,
                                                                    'entry', None,
                                                                    'exit', None,
                                                                    'location', None,
                                                                    'mode', None,
                                                                    'progress_measure', None,
                                                                    'score_scaled', None,
                                                                    'score_raw', None,
                                                                    'total_time', None,
                                                                    'time_tracked', None,
                                                                    'success_status', True,
                                                                    'suspend_data', None,
                                                                    'learner_preference', None,
                                                                    'static', None,
                                                                    'comments_from_learner', [],
                                                                    'comments_from_lms', [],
                                                                    'interactions', [],
                                                                    'objectives', []))))
