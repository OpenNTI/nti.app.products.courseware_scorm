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
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.interface.interfaces import ComponentLookupError

from zope.component.interfaces import ISite

from zope.event import notify

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

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.contenttypes.completion.interfaces import UserProgressUpdatedEvent

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
        metadata = ISCORMCourseMetadata(self.context, None)
        scorm_id = getattr(metadata, 'scorm_id', None)
        if scorm_id:
            client.unregister_users_for_scorm_content(scorm_id)
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
        metadata = ISCORMCourseMetadata(self.context, None)
        scorm_id = getattr(metadata, 'scorm_id', None)
        registration_list = []
        if scorm_id:
            registration_list = client.get_registration_list(scorm_id)
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
        metadata = ISCORMCourseMetadata(self.context, None)
        scorm_id = getattr(metadata, 'scorm_id', None)
        client = component.getUtility(ISCORMCloudClient)
        result = client.get_archive(scorm_id)
        zip_bytes = result
        metadata = client.get_metadata(scorm_id)
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
            notify(UserProgressUpdatedEvent(obj=metadata,
                                            user=user,
                                            context=course))
            return report
        else:
            container.remove_registration_report(user)
            return hexc.HTTPNoContent()



_SC_UTILITY_NAME = 'scormcloud_client'
        
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=ISite,
               request_method='GET',
               permission=nauth.ACT_NTI_ADMIN,
               name="ScormCloudClient")
class ManageScormConfigurationView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):
    """
    APIs for seeing what scorm cloud client a site is using and
    registering/unregistering them persistently. At this point these
    are intended to be internal and used by operations group. They
    aren't current expected to be exposed to client applications or
    outside users. As such it's a named view not registered as a link anywhere.
    """

    @view_config(request_method='GET')
    def get_client(self):
        """
        A GET to this named view return the registered ISCORMCloudClient
        that will be used by the ISite (context). This utility may not come from this
        sites registry and it may or may not be persistent.
        """
        sm = self.context.getSiteManager()
        try:
            return sm.getUtility(ISCORMCloudClient)
        except ComponentLookupError:
            raise hexc.HTTPNotFound()

    @view_config(request_method='POST')
    def make_client(self):
        """
        POSTing an ISCORMCloudClient object to this view will create a
        persistent client, store it beneath the SiteManager's default
        folder and register it as a utility as appropriate. If a
        persistent ISCORMCloudClient already exists in this SiteManager
        a 409 conflict is raised.
        """
        sm = self.context.getSiteManager()
        smf = sm['default']
        client = None
        try:
            client = smf[_SC_UTILITY_NAME]
        except KeyError:
            pass

        if client is not None:
            raise hexc.HTTPConflict()

        client = self.readCreateUpdateContentObject(self.remoteUser)

        sm.registerUtility(client, ISCORMCloudClient, '')
        smf[_SC_UTILITY_NAME] = client
        
        return client

    @view_config(request_method='DELETE')
    def nuke_client(self):
        """
        DELETEing this view will delete and unregister the persistent
        ISCORMCloudClient stored (and registered) in this Site
        Manager. If this SiteManager does not have a persitent
        ISCORMCloudClient a 404 is returned.
        """
        sm = self.context.getSiteManager()
        smf = sm['default']
        try:
            client = smf[_SC_UTILITY_NAME]
        except KeyError:
            raise hexc.HTTPNotFound()

        
        sm.unregisterUtility(client, provided=ISCORMCloudClient)
        del smf[_SC_UTILITY_NAME]
        return hexc.HTTPNoContent()


