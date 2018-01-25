#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.app.products.courseware_scorm import IScormInstance
from nti.app.products.courseware_scorm import IScormRegistration

from nti.scorm_cloud.client.registration import Instance
from nti.scorm_cloud.client.registration import Registration


@interface.implementer(IScormInstance)
class ScormInstance(Object):

    def __init__(self, instance):
        """
        Initializes `self` using the data from an `Instance` object.
        """
        self.course_version = instance.courseVersion
        self.instance_id = instance.instanceId
        self.update_date = instance.updateDate

@interface.implementer(IScormRegistration)
class ScormRegistration(Object):

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
        self.instances = [ScormInstance(instance) for instance in registration.instances]
        self.last_access_date = registration.lastAccessDate
        self.last_course_version_launched = registration.lastCourseVersionLaunched
        self.learner_id = registration.learnerId
        self.learner_first_name = registration.learnerFirstName
        self.learner_last_name = registration.learnerLastName
