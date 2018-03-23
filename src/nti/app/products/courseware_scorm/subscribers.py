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
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.contenttypes.completion.interfaces import IRequiredCompletableItemProvider

from nti.contenttypes.courses.interfaces import ICourseInstanceRemovedEvent
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.coremetadata.interfaces import IUser

logger = __import__('logging').getLogger(__name__)


@component.adapter(ICourseInstanceEnrollmentRecord, IBeforeIdRemovedEvent)
def _enrollment_record_dropped(record, unused_event):
    course = record.CourseInstance
    if ISCORMCourseInstance.providedBy(course):
        client = component.queryUtility(ISCORMCloudClient)
        if client is not None:
            client.delete_enrollment_record(record)


@component.adapter(ISCORMCourseInstance, ICourseInstanceRemovedEvent)
def _on_course_instance_removed(course, event):
    metadata = ISCORMCourseMetadata(course, None)
    if metadata is not None and metadata.has_scorm_package():
        client = component.getUtility(ISCORMCloudClient)
        client.delete_course(course)


@component.adapter(IAllCoursesCollection)
@interface.implementer(IAllCoursesCollectionAcceptsProvider)
class SCORMAllCoursesCollectionAcceptsProvider(object):

    def __init__(self, courses_collection):
        self.courses_collection = courses_collection

    def __iter__(self):
        if component.queryUtility(ISCORMCloudClient) is not None:
            return iter([SCORM_COURSE_MIME_TYPE])
        return iter(())


@component.adapter(IUser, ISCORMCourseInstance)
@interface.implementer(IRequiredCompletableItemProvider)
class _SCORMCompletableItemProvider(object):
    
    def __init__(self, user, course):
        self.user = user
        self.course = course
        
    def iter_items(self):
        metadata = ISCORMCourseMetadata(self.course)
        return [metadata]
    