#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import component

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.courseware_admin.views.management_views import CreateCourseView
from nti.app.products.courseware_admin.views.management_views import DeleteCourseView

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import IMPORT_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import UPLOAD_SCORM_COURSE_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseAdministrativeLevel

from nti.dataserver import authorization as nauth

from nti.scorm_cloud.client.mixins import get_source


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseAdministrativeLevel,
             request_method='POST',
             permission=nauth.ACT_NTI_ADMIN,
             name=CREATE_SCORM_COURSE_VIEW_NAME)
class CreateSCORMCourseView(CreateCourseView):
    """
    An object that can create SCORM courses.
    """

    _COURSE_INSTANCE_FACTORY = SCORMCourseInstance


class DeleteSCORMCourseView(DeleteCourseView):
    """
    A view for deleting SCORM courses.
    """


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseAdministrativeLevel,
             request_method='POST',
             permission=nauth.ACT_NTI_ADMIN,
             name=UPLOAD_SCORM_COURSE_VIEW_NAME)
class UploadSCORMCourseView(AbstractAuthenticatedView,
                            ModeledContentUploadRequestUtilsMixin):
    """
    A view for uploading SCORM course zip archives to SCORM Cloud.
    """

    def __call__(self):
        sources = get_all_sources(self.request)
        if sources:
            _handle_multipart(sources)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='POST',
             permission=nauth.ACT_NTI_ADMIN,
             name=IMPORT_SCORM_COURSE_VIEW_NAME)
class ImportSCORMCourseView(AbstractAuthenticatedView,
                            ModeledContentUploadRequestUtilsMixin):
    """
    A view for importing uploaded SCORM courses to SCORM Cloud.
    """

    def __call__(self):
        sources = get_all_sources(self.request)
        if sources:
            source = self._handle_multipart(sources)
        if not source:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"No SCORM zip file was included with request."),
                             },
                             None)
        client = component.getUtility(ISCORMCloudClient)
        client.import_course(self.context, source)

        enrollments = ICourseEnrollments(self.context)
        for record in enrollments.iter_enrollments():
            client.sync_enrollment_record(record, self.context)

        return hexc.HTTPNoContent()

    def _handle_multipart(self, sources):
        """
        Returns a file source from the sources sent in a multi-part request.
        """
        for key in sources:
            raw_source = sources.get(key)
            source = get_source(raw_source)
            if source:
                break
        return source
