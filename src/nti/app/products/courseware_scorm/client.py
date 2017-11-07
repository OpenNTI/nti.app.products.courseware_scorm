#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from pyramid.httpexceptions import HTTPFound

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.scorm_cloud.client import ScormCloudService
from nti.scorm_cloud.client import ScormCloudUtilities


# TODO: Use real values for these
appId = ""    # e.g."3ABCDJHRT"
secretKey = ""    # e.g."aBCDEF7o8AOF7qsP0649KfLyXOlfgyxyyt7ecd2U"
serviceUrl = "http://cloud.scorm.com/EngineWebServices"
origin = ScormCloudUtilities.get_canonical_origin_string('your company',
                                                         'sample application', '1.0')
cloud = ScormCloudService.withargs(appId, secretKey, serviceUrl, origin)


@interface.implementer(ISCORMCloudClient)
class SCORMCloudClient(object):
    """
    The default SCORM client.
    """

    def import_SCORM_course(self, path):
        """
        Imports a SCORM course into SCORM Cloud.

        :param path The relative path of the zip file to import.
        """
        cloud_service = cloud.get_course_service()
        unused_importResult = cloud_service.import_uploaded_course(None, path)

        up_service = cloud.get_upload_service()
        unused_response = up_service.delete_file(path)

        # TODO: Use a real redirect URL
        redirectUrl = 'sample/courselist'
        return HTTPFound(location=redirectUrl)