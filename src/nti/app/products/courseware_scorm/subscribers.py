#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zc.intid.interfaces import IBeforeIdRemovedEvent

from zope import component

from zope.intid.interfaces import IIntIdAddedEvent

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

logger = __import__('logging').getLogger(__name__)


@component.adapter(ICourseInstanceEnrollmentRecord, IIntIdAddedEvent)
def _enrollment_record_created(record, unused_event):
    course = record.CourseInstance
    if ISCORMCourseInstance.providedBy(course):
        client = component.getUtility(ISCORMCloudClient)
        client.sync_enrollment_record(record, course)


@component.adapter(ICourseInstanceEnrollmentRecord, IBeforeIdRemovedEvent)
def _enrollment_record_dropped(record, unused_event):
    if ISCORMCourseInstance.providedBy(course):
        client = component.getUtility(ISCORMCloudClient)
        client.delete_enrollment_record(record)
