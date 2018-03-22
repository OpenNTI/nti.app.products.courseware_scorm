#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from persistent import Persistent

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from zope.container.contained import Contained

from zope.intid.interfaces import IIntIds

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.contenttypes.courses.courses import CourseInstance

from nti.contenttypes.courses.utils import is_course_editor

from nti.dataserver import authorization as nauth

SCORM_COURSE_METADATA_KEY = 'nti.app.produts.courseware_scorm.courses.metadata'
SCORM_COURSE_MIME_TYPE = 'application/vnd.nextthought.courses.scormcourseinstance'

logger = __import__('logging').getLogger(__name__)


def is_course_admin(user, course):
    return is_course_editor(course, user) \
        or nauth.is_admin_or_content_admin_or_site_admin(user)


@interface.implementer(ISCORMCourseInstance)
class SCORMCourseInstance(CourseInstance):
    """
    An instance of a SCORM course.
    """

    mime_type = mimeType = SCORM_COURSE_MIME_TYPE

    __external_can_create__ = True


@component.adapter(ISCORMCourseInstance)
@interface.implementer(ISCORMCourseMetadata)
class SCORMCourseMetadata(Persistent, Contained):
    """
    A metadata object for a SCORM course instance.
    """

    scorm_id = None

    def has_scorm_package(self):
        return self.scorm_id is not None

SCORMCourseInstanceMetadataFactory = an_factory(SCORMCourseMetadata,
                                                SCORM_COURSE_METADATA_KEY)


@component.adapter(ISCORMCourseMetadata)
@interface.implementer(IUserRegistrationReportContainer)
class UserRegistrationReportContainer(CaseInsensitiveCheckingLastModifiedBTreeContainer):
    
    def add_registration_report(self, registration_report, user):
        self[user.username] = registration_report
    
    def get_registration_report(self, user):
        return self.get(user.username)
    
    def remove_registration_report(self, user):
        try:
            del self[user.username]
            result = True
        except KeyError:
            result = False
        return result
@interface.implementer(ISCORMIdentifier)
class SCORMIdentifier(object):

    def __init__(self, obj):
        self.object = obj

    def get_id(self):
        # NTIIDs contain characters invalid for SCORM IDs, so use IntId
        intids = component.getUtility(IIntIds)
        return str(intids.getId(self.object))


@interface.implementer(ISCORMIdentifier)
class SCORMRegistrationIdentifier(object):

    def __init__(self, user, course):
        self.user = user
        self.course = course

    def get_id(self):
        intids = component.getUtility(IIntIds)
        user_id = str(intids.getId(self.user))
        course_id = str(intids.getId(self.course))
        return u'-'.join([user_id, course_id])
