#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os

from persistent import Persistent

from six.moves import cStringIO

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from zope.container.contained import Contained

from zope.event import notify

from zope.intid.interfaces import IIntIds

from nti.app.products.courseware_scorm import SCORM_COLLECTION_NAME

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IRegistrationReportContainer
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationRemovedEvent
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.app.products.courseware_scorm.model import SCORMContentInfoContainer

from nti.cabinet.filer import transfer_to_native_file

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.contentlibrary.interfaces import IFilesystemBucket

from nti.contentlibrary.presentationresource import DisplayableContentMixin

from nti.contenttypes.completion.interfaces import UserProgressRemovedEvent

from nti.contenttypes.courses.courses import CourseInstance

from nti.contenttypes.courses.exporter import BaseSectionExporter

from nti.contenttypes.courses.importer import BaseSectionImporter

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseSectionExporter
from nti.contenttypes.courses.interfaces import ICourseSectionImporter

from nti.contenttypes.courses.utils import is_course_instructor_or_editor

from nti.dataserver import authorization as nauth

from nti.ntiids.oids import to_external_ntiid_oid

SCORM_COURSE_METADATA_KEY = 'nti.app.produts.courseware_scorm.courses.metadata'
SCORM_CONTENT_CONTAINER_KEY = 'nti.app.products.courseware_scorm.courses.content_container'

SCORM_COURSE_MIME_TYPE = 'application/vnd.nextthought.courses.scormcourseinstance'

REGISTRATION_REPORT_CONTAINER_KEY = 'nti.app.products.courseware_scorm.courses.registration-report-container'

logger = __import__('logging').getLogger(__name__)


def is_course_admin(user, course):
    return is_course_instructor_or_editor(course, user) \
        or nauth.is_admin_or_content_admin_or_site_admin(user)


@interface.implementer(ISCORMCourseInstance)
class SCORMCourseInstance(CourseInstance, DisplayableContentMixin):
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

    @property
    def ntiid(self):
        return to_external_ntiid_oid(self)

    def has_scorm_package(self):
        return self.scorm_id is not None


SCORMCourseInstanceMetadataFactory = an_factory(SCORMCourseMetadata,
                                                SCORM_COURSE_METADATA_KEY)

SCORMContentContainerFactory = an_factory(SCORMContentInfoContainer,
                                          SCORM_COLLECTION_NAME)


@interface.implementer(ISCORMRegistrationRemovedEvent)
class SCORMRegistrationRemovedEvent(object):

    def __init__(self, registration_id, course, user):
        self.registration_id = registration_id
        self.course = course
        self.user = user


@component.adapter(ICourseInstance)
@interface.implementer(IRegistrationReportContainer)
class RegistrationReportContainer(CaseInsensitiveCheckingLastModifiedBTreeContainer):

    def clear(self):
        if len(self) == 0:
            return
        for key, value in list(self.items()):
            value.clear()
            del self[key]


RegistrationReportContainerFactory = an_factory(RegistrationReportContainer,
                                                REGISTRATION_REPORT_CONTAINER_KEY)


@interface.implementer(IUserRegistrationReportContainer)
class UserRegistrationReportContainer(CaseInsensitiveCheckingLastModifiedBTreeContainer):

    def add_registration_report(self, scorm_id, registration_report):
        self[scorm_id] = registration_report

    def get_registration_report(self, scorm_id):
        return self.get(scorm_id)

    def remove_registration_report(self, scorm_id):
        if scorm_id is None:
            return False
        try:
            del self[scorm_id]
            result = True
        except KeyError:
            result = False
        return result


@component.adapter(ISCORMRegistrationRemovedEvent)
def _on_scorm_registration_removed(event):
    logger.debug(u'_on_scorm_registration_removed: regid=%s', event.registration_id)
    user = event.user
    if user is None:
        return
    course = event.course
    metadata = ISCORMCourseMetadata(course)
    # Remove any persisted CompletedItems
    notify(UserProgressRemovedEvent(obj=metadata,
                                    user=user,
                                    context=course))
    # Remove any stored registration report
    container = IUserRegistrationReportContainer(metadata)
    container.remove_registration_report(user)


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

    @classmethod
    def get_user(cls, registration_id):
        intids = component.getUtility(IIntIds)
        parts = registration_id.split(u'-')
        return intids.queryObject(int(parts[0]))


SCORM_PACKAGE_NAME = u'SCORMPackage.zip'

@interface.implementer(ICourseSectionExporter)
class CourseSCORMPackageExporter(BaseSectionExporter):

    def export(self, course, filer, backup=True, salt=None):
        client = component.queryUtility(ISCORMCloudClient)
        if client is None:
            logger.warn("Exporting SCORM content without client configured.")
            return
        archive = client.get_archive(course)
        if archive is None:
            return
        filer.default_bucket = bucket = self.course_bucket(course)
        source = cStringIO(archive)
        filename = SCORM_PACKAGE_NAME
        filer.save(filename,
                   source,
                   contentType='application/zip; charset=UTF-8',
                   bucket=bucket,
                   overwrite=True)


@interface.implementer(ICourseSectionImporter)
class CourseSCORMPackageImporter(BaseSectionImporter):

    def process(self, course, filer, writeout=True):
        path = self.course_bucket_path(course) + SCORM_PACKAGE_NAME
        source = self.safe_get(filer, path)
        if source is None:
            return
        client = component.queryUtility(ISCORMCloudClient)
        if client is None:
            logger.warn("Importing SCORM content without client configured.")
            return
        client.import_course(course, source)
        # Save source
        if writeout and IFilesystemBucket.providedBy(course.root):
            path = self.course_bucket_path(course) + SCORM_PACKAGE_NAME
            source = self.safe_get(filer, path) # Reload
            if source is not None:
                self.makedirs(course.root.absolute_path)
                new_path = os.path.join(course.root.absolute_path,
                                        SCORM_PACKAGE_NAME)
                transfer_to_native_file(source, new_path)
