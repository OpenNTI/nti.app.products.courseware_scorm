#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import readproperty

from zope.component.hooks import getSite

from zope.container.contained import Contained

from zope.intid.interfaces import IIntIds

from nti.app.products.courseware_scorm.interfaces import ISCORMStatic
from nti.app.products.courseware_scorm.interfaces import ISCORMComment
from nti.app.products.courseware_scorm.interfaces import ISCORMRuntime
from nti.app.products.courseware_scorm.interfaces import ISCORMActivity
from nti.app.products.courseware_scorm.interfaces import IScormInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMResponse
from nti.app.products.courseware_scorm.interfaces import ISCORMObjective
from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo
from nti.app.products.courseware_scorm.interfaces import ISCORMInteraction
from nti.app.products.courseware_scorm.interfaces import IScormRegistration
from nti.app.products.courseware_scorm.interfaces import ISCORMLearnerPreference
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationReport
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfoContainer

from nti.app.products.courseware_scorm.workspaces import SCORMInstanceCollection

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.presentation.mixins import PersistentPresentationAsset

from nti.dataserver.authorization_acl import acl_from_aces

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.ntiids.oids import to_external_ntiid_oid

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

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

logger = __import__('logging').getLogger(__name__)


def _parse_float(str_value, name):
    float_value = None
    if str_value is None:
        return float_value
    try:
        float_value = float(str_value)
    except (TypeError, ValueError):
        logger.info(u'Found non-float value %s for property %s',
                    str_value, name)
    return float_value


def _parse_int(str_value, name):
    int_value = None
    if str_value is None:
        return int_value
    try:
        int_value = int(str_value)
    except (TypeError, ValueError):
        logger.info(u'Found non-int value %s for property %s',
                    str_value, name)
    return int_value


def _parse_time(str_value, name):
    time = None
    if str_value is None:
        return time
    try:
        # Parses "H:M:S.ms" and "S.ms"
        sec_min_hour = reversed([float(x) for x in str_value.split(':')])
        time = sum([x*y for x,y in zip(sec_min_hour, (1, 60, 3600))])
    except ValueError as error:
        logger.info('%s: %s', name, error)
    return time


def _parse_datetime(str_value, name):
    datetime_value = None
    if str_value is None:
        return datetime_value
    try:
        datetime_value = datetime.strptime(str_value, '%Y%m%d%H%M%S')
    except ValueError as error:
        logger.info('%s: %s', name, error)
    return datetime_value


def _response(value):
    response = None
    if value is None:
        return response
    if type(value) is Response:
        response = value
    else:
        response = Response(id_=u'', value=value)
    return ISCORMResponse(response)


@EqHash('target')
@interface.implementer(ISCORMContentRef)
class SCORMContentRef(PersistentPresentationAsset):

    createDirectFieldProperties(ISCORMContentRef)

    __external_class_name__ = "SCORMContentRef"
    mime_type = mimeType = 'application/vnd.nextthought.scormcontentref'

    __name__ = alias('ntiid')

    @readproperty
    def ntiid(self):  # pylint: disable=method-hidden
        self.ntiid = self.generate_ntiid(u'SCORMContentRef')
        return self.ntiid


@interface.implementer(ISCORMContentInfo)
class ScormContentInfo(PersistentCreatedAndModifiedTimeObject,
                       Contained,
                       SchemaConfigured):

    createDirectFieldProperties(ISCORMContentInfo)

    __parent__ = None
    __name__ = None

    creator = None
    NTIID = alias('ntiid')

    mimeType = mime_type = "application/vnd.nextthought.scorm.scormcontentinfo"

    @Lazy
    def ntiid(self):
        return to_external_ntiid_oid(self)

    @LazyOnClass
    def __acl__(self):
        # If we don't have this, it would derive one from ICreated, rather than its parent.
        return acl_from_aces([])


@component.adapter(CourseData)
@interface.implementer(ISCORMContentInfo)
def _course_data_to_scorm_content_info(course_data):
    try:
        reg_count = int(course_data.numberOfRegistrations)
    except (TypeError, ValueError):
        reg_count = None
    return ScormContentInfo(scorm_id=course_data.courseId,
                            course_version=course_data.numberOfVersions,
                            title=course_data.title,
                            tags=course_data.tags or (),
                            registration_count=reg_count)


@component.adapter(ICourseInstance)
@interface.implementer(ISCORMContentInfoContainer)
class SCORMContentInfoContainer(CaseInsensitiveCheckingLastModifiedBTreeContainer,
                                SchemaConfigured,
                                SCORMInstanceCollection):

    __external_can_create__ = False

    mimeType = mime_type = "application/vnd.nextthought.scorm.scorm_content_info_container"

    createDirectFieldProperties(ISCORMContentInfoContainer)

    creator = None

    def __init__(self, *args, **kwargs):
        CaseInsensitiveCheckingLastModifiedBTreeContainer.__init__(self)
        SchemaConfigured.__init__(self, *args, **kwargs)

    @Lazy
    def tags(self):
        intids = component.getUtility(IIntIds)
        return (str(intids.getId(self.__parent__)),
                getSite().__name__)

    def _include_filter(self, unused_scorm_content):
        return True

    @property
    def scorm_instances(self):
        """
        Return available scorm instances.
        """
        return tuple(self.values())

    def store_content(self, content):
        self[content.scorm_id] = content
        return content

    def remove_content(self, content):
        key = getattr(content, 'scorm_id', content)
        try:
            del self[key]
            result = True
        except KeyError:
            result = False
        return result

    @Lazy
    def ntiid(self):
        return to_external_ntiid_oid(self)


@component.adapter(Instance)
@interface.implementer(IScormInstance)
class ScormInstance(object):

    def __init__(self, instance):
        """
        Initializes `self` using the data from an `Instance` object.
        """
        self.course_version = instance.courseVersion
        self.instance_id = instance.instanceId
        self.update_date = instance.updateDate


@component.adapter(Registration)
@interface.implementer(IScormRegistration)
class ScormRegistration(object):

    def __init__(self, registration):
        """
        Initializes `self` using the data from a `Registration` object.
        """
        self.app_id = registration.appId
        self.course_id = registration.courseId
        self.registration_id = registration.registrationId
        self.completed_date = registration.completedDate
        self.course_title = registration.courseTitle
        self.create_date = registration.createDate
        self.email = registration.email
        self.first_access_date = registration.firstAccessDate
        self.instances = [
            ScormInstance(instance) for instance in registration.instances
        ]
        self.last_access_date = registration.lastAccessDate
        self.last_course_version_launched = registration.lastCourseVersionLaunched
        self.learner_id = registration.learnerId
        self.learner_first_name = registration.learnerFirstName
        self.learner_last_name = registration.learnerLastName


@component.adapter(RegistrationReport)
@interface.implementer(ISCORMRegistrationReport)
class SCORMRegistrationReport(object):

    def __init__(self, registration_report):
        self.format = registration_report.format
        self.registration_id = registration_report.regid
        self.instance_id = registration_report.instanceid
        if registration_report.activity is not None:
            self.activity = ISCORMActivity(registration_report.activity)
        else:
            self.activity = None
        self.complete = registration_report.complete == u'complete'
        self.success = registration_report.success == u'passed'
        self.score = _parse_int(registration_report.score, u'score')
        self.total_time = _parse_int(registration_report.totaltime, u'total_time')


@component.adapter(Objective)
@interface.implementer(ISCORMObjective)
class SCORMObjective(object):

    def __init__(self, objective):
        self.id = objective.id
        self.measure_status = objective.measurestatus
        self.normalized_measure = _parse_float(objective.normalizedmeasure, u'SCORMObjective.normalized_measure')
        self.progress_status = objective.progressstatus
        self.satisfied_status = objective.satisfiedstatus
        self.score_scaled = _parse_float(objective.score_scaled, u'SCORMObjective.score_scaled')
        self.score_min = _parse_float(objective.score_min, u'SCORMObjective.score_min')
        self.score_raw = _parse_float(objective.score_raw, u'SCORMObjective.score_raw')
        self.success_status = {u'passed': True, u'failed': False}.get(objective.success_status)
        self.completion_status = objective.completion_status
        self.progress_measure = _parse_float(objective.progress_measure, u'SCORMObjective.progress_measure')
        self.description = objective.description


@component.adapter(Activity)
@interface.implementer(ISCORMActivity)
class SCORMActivity(object):

    def __init__(self, activity):
        self.id = activity.id
        self.title = activity.title
        self.complete = {u'complete': True, u'incomplete': False}.get(activity.complete)
        self.success = {u'passed': True, u'failed': False}.get(activity.success)
        self.satisfied = activity.satisfied
        self.completed = activity.completed
        self.progress_status = activity.progressstatus
        self.attempts = activity.attempts
        self.suspended = activity.suspended
        self.time = _parse_time(activity.time, u'SCORMActivity.time')
        self.score = _parse_float(activity.score, u'SCORMActivity.score')
        self.objectives = [ISCORMObjective(obj) for obj in activity.objectives]
        self.children = [SCORMActivity(child) for child in activity.children]
        if activity.runtime is not None:
            self.runtime = ISCORMRuntime(activity.runtime)
        else:
            self.runtime = None


@component.adapter(Response)
@interface.implementer(ISCORMResponse)
class SCORMResponse(object):

        def __init__(self, response):
            self.id = response.id
            self.value = response.value


@component.adapter(Interaction)
@interface.implementer(ISCORMInteraction)
class SCORMInteraction(object):

    def __init__(self, interaction):
        self.id = interaction.id
        self.result = interaction.result
        self.latency = _parse_time(interaction.latency, u'SCORMInteraction.latency')
        self.timestamp = _parse_time(interaction.timestamp, u'SCORMInteraction.timestamp')
        self.weighting = _parse_float(interaction.weighting, u'SCORMInteraction.weighting')
        self.objectives = [ISCORMObjective(obj) for obj in interaction.objectives]
        self.description = interaction.description
        self.learner_response = _response(interaction.learner_response)
        if interaction.correct_responses is not None:
            self.correct_responses = [_response(r) for r in interaction.correct_responses]
        else:
            self.correct_responses = None


@component.adapter(Comment)
@interface.implementer(ISCORMComment)
class SCORMComment(object):

        def __init__(self, comment):
            self.value = comment.value
            self.location = comment.location
            self.date_time = _parse_datetime(comment.date_time, u'SCORMComment.date_time')


@component.adapter(LearnerPreference)
@interface.implementer(ISCORMLearnerPreference)
class SCORMLearnerPreference(object):

    def __init__(self, learner_preference):
        self.language = learner_preference.language
        self.audio_level = _parse_float(learner_preference.audio_level, u'SCORMLearnerPreference.audio_level')
        self.delivery_speed = _parse_float(learner_preference.delivery_speed, u'SCORMLearnerPreference.delivery_speed')
        self.audio_captioning = learner_preference.audio_captioning


@component.adapter(Static)
@interface.implementer(ISCORMStatic)
class SCORMStatic(object):

    def __init__(self, static):
        self.learner_id = static.learner_id
        self.launch_data = static.launch_data
        self.learner_name=static.learner_name
        self.max_time_allowed = _parse_time(static.max_time_allowed, u'SCORMStatic.max_time_allowed')
        self.time_limit_action = static.time_limit_action
        self.completion_threshold = _parse_float(static.completion_threshold, u'SCORMStatic.completion_threshold')
        self.scaled_passing_score = _parse_float(static.scaled_passing_score, u'SCORMStatic.scaled_passing_score')


@component.adapter(Runtime)
@interface.implementer(ISCORMRuntime)
class SCORMRuntime(object):

    def __init__(self, runtime):
        self.mode = runtime.mode
        self.exit = runtime.exit
        self.entry = runtime.entry
        self.credit = {u'credit': True, u'no-credit': False}.get(runtime.credit)
        if runtime.static is not None:
            self.static = ISCORMStatic(runtime.static)
        else:
            self.static = None
        self.location = runtime.location
        self.score_raw = _parse_float(runtime.score_raw, u'SCORMRuntime.score_raw')
        self.objectives = [ISCORMObjective(obj) for obj in runtime.objectives]
        self.total_time = _parse_time(runtime.total_time, u'SCORMRuntime.total_time')
        self.time_tracked = _parse_time(runtime.timetracked, u'SCORMRuntime.time_tracked')
        self.interactions = [ISCORMInteraction(i) for i in runtime.interactions]
        self.score_scaled = _parse_float(runtime.score_scaled, u'SCORMRuntime.score_scaled')
        self.suspend_data = runtime.suspend_data
        self.success_status = {u'passed': True, u'failed': False}.get(runtime.success_status)
        self.progress_measure = _parse_float(runtime.progress_measure, u'SCORMRuntime.progress_measure')
        self.completion_status = runtime.completion_status
        if runtime.learnerpreference is not None:
            self.learner_preference = ISCORMLearnerPreference(runtime.learnerpreference)
        else:
            self.learner_preference = None
        self.comments_from_lms = [ISCORMComment(c) for c in runtime.comments_from_lms]
        self.comments_from_learner = [ISCORMComment(c) for c in runtime.comments_from_learner]
