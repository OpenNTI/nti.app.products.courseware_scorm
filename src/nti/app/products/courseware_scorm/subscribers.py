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
from zope import interface

from zope.intid.interfaces import IIntIdAddedEvent

from nti.app.products.courseware.interfaces import IAllCoursesCollection
from nti.app.products.courseware.interfaces import IAllCoursesCollectionAcceptsProvider

from nti.app.products.courseware_scorm.courses import SCORM_COURSE_MIME_TYPE

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
    course = record.CourseInstance
    if ISCORMCourseInstance.providedBy(course):
        client = component.getUtility(ISCORMCloudClient)
        client.delete_enrollment_record(record)


@component.adapter(IAllCoursesCollection)
@interface.implementer(IAllCoursesCollectionAcceptsProvider)
class SCORMAllCoursesCollectionAcceptsProvider(object):

    def __init__(self, courses_collection):
        self.courses_collection = courses_collection

    def __iter__(self):
        from IPython.terminal.debugger import set_trace;set_trace()
        if component.queryUtility(ISCORMCloudClient) is not None:
            return iter([SCORM_COURSE_MIME_TYPE])
        else:
            return iter([])
