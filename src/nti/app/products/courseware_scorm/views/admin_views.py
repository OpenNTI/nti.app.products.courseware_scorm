#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from six.moves import cStringIO

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from zope import component

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.courses import is_course_admin

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.app.products.courseware_scorm.views import GET_SCORM_ARCHIVE_VIEW_NAME
from nti.app.products.courseware_scorm.views import GET_REGISTRATION_LIST_VIEW_NAME
from nti.app.products.courseware_scorm.views import DELETE_ALL_REGISTRATIONS_VIEW_NAME
from nti.app.products.courseware_scorm.views import SYNC_REGISTRATION_REPORT_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver import authorization as nauth

from nti.dataserver.users.users import User

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=nauth.ACT_NTI_ADMIN,
             name=DELETE_ALL_REGISTRATIONS_VIEW_NAME)
class DeleteAllRegistrationsView(AbstractAuthenticatedView):
    """
    A view which allows admins to delete all SCORM registrations.
    """

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        client.delete_all_registrations(self.context)
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=nauth.ACT_NTI_ADMIN,
             name=GET_REGISTRATION_LIST_VIEW_NAME)
class GetRegistrationListView(AbstractAuthenticatedView):
    """
    A view which returns the SCORM Cloud registration list.
    """

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        registration_list = client.get_registration_list(self.context)
        result = LocatedExternalDict()
        result[ITEMS] = registration_list
        result[ITEM_COUNT] = result[TOTAL] = len(registration_list)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             name=GET_SCORM_ARCHIVE_VIEW_NAME)
class GetArchiveView(AbstractAuthenticatedView):
    """
    A view which returns the SCORM course archive.
    """

    def __call__(self):
        if not is_course_admin(user=self.remoteUser, course=self.context):
            return hexc.HTTPForbidden(_(u"You do not have access to this SCORM content."))
        client = component.getUtility(ISCORMCloudClient)
        result = client.get_archive(self.context)
        zip_bytes = result
        metadata = client.get_metadata(self.context)
        return self._export_archive(zip_bytes, metadata, self.request.response)

    def _export_archive(self, zip_bytes, metadata, response):
        filename = '%s.zip' % metadata.title
        response.content_encoding = 'identity'
        response.content_type = 'application/zip; charset=UTF-8'
        content_disposition = 'attachment; filename="%s"' % filename
        response.content_disposition = str(content_disposition)
        zip_io = cStringIO(zip_bytes)
        response.body_file = zip_io
        return response
    

@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstanceEnrollment,
             request_method='POST',
             name=SYNC_REGISTRATION_REPORT_VIEW_NAME)
class SyncRegistrationReportView(AbstractAuthenticatedView):
    
    def _results_format(self):
        return CaseInsensitiveDict(self.request.params).get(u'resultsFormat')
    
    def __call__(self):
        user = User.get_user(self.context.Username)
        course = self.context.CourseInstance
        if not is_course_admin(user=self.remoteUser, course=course):
            return hexc.HTTPForbidden(_(u"You do not have access to this SCORM content."))
        client = component.getUtility(ISCORMCloudClient)
        metadata = ISCORMCourseMetadata(course)
        container = IUserRegistrationReportContainer(metadata)
        if client.enrollment_registration_exists(course, user):
            report = client.get_registration_progress(course, user, self._results_format())
            container.add_registration_report(report, user)
            return report
        else:
            container.remove_registration_report(user)
            return hexc.HTTPNoContent()
            