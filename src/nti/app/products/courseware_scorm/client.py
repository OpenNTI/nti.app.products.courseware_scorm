#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from pyramid.httpexceptions import HTTPFound

from nti.app.externalization.error import raise_json_error

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import IScormIdentifier

from nti.scorm_cloud.interfaces import IScormCloudService
from nti.scorm_cloud.client import ScormCloudService
from nti.scorm_cloud.client import ScormCloudUtilities

SERVICE_URL = "http://cloud.scorm.com/EngineWebServices"


@interface.implementer(ISCORMCloudClient)
class SCORMCloudClient(object):
    """
    The default SCORM client.
    """

    def __init__(self, app_id, secret_key):
        self.app_id = app_id
        self.secret_key = secret_key
        origin = ScormCloudUtilities.get_canonical_origin_string('NextThought',
                                                                 'Platform', '1.0')
        service = component.getUtility(IScormCloudService)
        self.cloud = service.withargs(app_id, secret_key, SERVICE_URL, origin)

    def import_course(self, context, source):
        """
        Imports a SCORM course zip file into SCORM Cloud.

        :param context: The course context under which to import the SCORM course.
        :param source: The zip file source of the course to import.
        :returns: The result of the SCORM Cloud import operation.
        """
        cloud_service = self.cloud.get_course_service()
        entry = ICourseCatalogEntry(context, context)
        scorm_id = IScormIdentifier(context).get_id()
        if scorm_id is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Uploading SCORM to a non-persistent course is forbidden."),
                             },
                             None)
        import_result = cloud_service.import_uploaded_course(scorm_id, source)

        return import_result


    def upload_course(self, source, redirect_url):
        """
        Uploads a SCORM course zip file to the SCORM Cloud server.

        :param source The SCORM course zip file to upload to SCORM Cloud.
        :param redirect_url The URL to which the client will be redirected after
            the upload completes.
        """
        upload_service = self.cloud.get_upload_service()
        cloud_upload_link = upload_service.get_upload_url(redirect_url)

        # TODO: Upload the zip bytes

        return HTTPFound(location=redirectUrl)
