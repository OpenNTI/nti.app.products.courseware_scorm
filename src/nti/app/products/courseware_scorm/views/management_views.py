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

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.views import UPDATE_SCORM_VIEW_NAME
from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import IMPORT_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import UPLOAD_SCORM_COURSE_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollments
from nti.contenttypes.courses.interfaces import ICourseAdministrativeLevel

from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.scorm_cloud.client.mixins import get_source
from nti.contenttypes.courses.utils import is_course_instructor_or_editor

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseAdministrativeLevel,
             request_method='POST',
             name=CREATE_SCORM_COURSE_VIEW_NAME)
class CreateSCORMCourseView(CreateCourseView):
    """
    An object that can create SCORM courses.
    """

    _COURSE_INSTANCE_FACTORY = SCORMCourseInstance


class AbstractAdminScormCourseView(AbstractAuthenticatedView):

    def _check_access(self):
        if      not is_admin_or_content_admin_or_site_admin(self.remoteUser) \
            and not is_course_instructor_or_editor(self.remoteUser):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'message': _(u"Cannot administer scorm courses."),
                             },
                             None)

    def __call__(self):
        self._check_access()
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseAdministrativeLevel,
             request_method='POST',
             name=UPLOAD_SCORM_COURSE_VIEW_NAME)
class UploadSCORMCourseView(AbstractAdminScormCourseView,
                            ModeledContentUploadRequestUtilsMixin):
    """
    A view for uploading SCORM course zip archives to SCORM Cloud.
    """

    def _handle_multipart(self, sources):
        raise NotImplementedError()

    def _do_call(self):
        sources = get_all_sources(self.request)
        if sources:
            self._handle_multipart(sources)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='POST',
             name=IMPORT_SCORM_COURSE_VIEW_NAME)
class ImportSCORMCourseView(AbstractAdminScormCourseView,
                            ModeledContentUploadRequestUtilsMixin):
    """
    A view for importing uploaded SCORM courses to SCORM Cloud.
    """

    def _do_call(self):
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

        # pylint: disable=too-many-function-args
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


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='POST',
             name=UPDATE_SCORM_VIEW_NAME)
class UpdateSCORMView(AbstractAdminScormCourseView,
                      ModeledContentUploadRequestUtilsMixin):

    def _do_call(self):
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
        client.update_assets(self.context, source, self.request)

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
