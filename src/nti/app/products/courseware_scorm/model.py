#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.products.courseware_scorm.interfaces import IScormInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMProgress
from nti.app.products.courseware_scorm.interfaces import ISCORMObjective
from nti.app.products.courseware_scorm.interfaces import IScormRegistration

from nti.scorm_cloud.client.registration import Instance
from nti.scorm_cloud.client.registration import Objective
from nti.scorm_cloud.client.registration import Registration
from nti.scorm_cloud.client.registration import RegistrationReport

logger = __import__('logging').getLogger(__name__)


def _parse_float(str_value, name):
        float_value = None
        try:
            float_value = float(str_value)
        except (TypeError, ValueError):
            logger.debug(u'Found non-float value %s for property %s',
                         str_value, name)
        return float_value
    

def _parse_int(str_value, name):
        int_value = None
        try:
            int_value = int(str_value)
        except (TypeError, ValueError):
            logger.debug(u'Found non-int value %s for property %s',
                         str_value, name)
        return int_value


def _parse_time(str_value, name):
    time = None
    if str_value is not None:
        time = sum([x*y for x,y in zip([float(x) for x in str_value.split(':')], (3600, 60, 1))])
    return time


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
@interface.implementer(ISCORMProgress)
class SCORMProgress(object):

    def __init__(self, registration_report):
        if registration_report.activity is not None:
            self.activity = registration_report.activity.__repr__()
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
