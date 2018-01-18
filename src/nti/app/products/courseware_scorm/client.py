#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nameparser import HumanName

from pyramid import httpexceptions as hexc

from zope import component
from zope import interface

from nti.app.externalization.error import raise_json_error

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.interfaces import IScormIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.users.users import User

from nti.externalization.proxy import removeAllProxies

from nti.scorm_cloud.client import ScormCloudUtilities

from nti.scorm_cloud.client.request import ScormCloudError

from nti.scorm_cloud.interfaces import IScormCloudService

SERVICE_URL = "http://cloud.scorm.com/EngineWebServices"

logger = __import__('logging').getLogger(__name__)


class ScormCourseNotFoundError(Exception):
    """
    An error raised on failure to find a course specified by courseid belonging to appid.
    """


class ScormCourseNoPasswordError(Exception):
    """
    An error raised when a postback URL login name is specified without password.
    """


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

    def import_course(self, context, source, request=None):
        """
        Imports a SCORM course zip file into SCORM Cloud.

        :param context: The course context under which to import the SCORM course.
        :param source: The zip file source of the course to import.
        :returns: The result of the SCORM Cloud import operation.
        """
        cloud_service = self.cloud.get_course_service()
        # pylint: disable=too-many-function-args
        scorm_id = IScormIdentifier(context).get_id()
        logger.info("Importing course using: app_id=%s scorm_id=%s",
                    self.app_id, scorm_id)
        if scorm_id is None:
            raise_json_error(request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Uploading SCORM to a non-persistent course is forbidden."),
                             },
                             None)
        cloud_service.import_uploaded_course(scorm_id, source)
        context = removeAllProxies(context)
        interface.alsoProvides(context, ISCORMCourseInstance)

        metadata = ISCORMCourseMetadata(context)
        metadata.scorm_id = scorm_id

        return context

    def upload_course(self, unused_source, redirect_url):
        """
        Uploads a SCORM course zip file to the SCORM Cloud server.

        :param source The SCORM course zip file to upload to SCORM Cloud.
        :param redirect_url The URL to which the client will be redirected after
            the upload completes.
        """
        upload_service = self.cloud.get_upload_service()
        cloud_upload_link = upload_service.get_upload_url(redirect_url)
        return hexc.HTTPFound(location=cloud_upload_link)

    def sync_enrollment_record(self, enrollment_record, course):
        """
        Syncs a course enrollment record with SCORM Cloud.
        """
        # pylint: disable=too-many-function-args
        course_id = IScormIdentifier(course).get_id()
        user = User.get_user(enrollment_record.Principal.id)
        learner_id = IScormIdentifier(user).get_id()
        reg_id = IScormIdentifier(enrollment_record).get_id()
        named = IFriendlyNamed(user)
        last_name = first_name = ''
        if named and named.realname:
            human_name = HumanName(named.realname)
            first_name = human_name.first
            last_name = human_name.last
        service = self.cloud.get_registration_service()
        logger.info("Syncing enrollment record: courseid=%s reg_id=%s fname=%s lname=%s learnerid=%s",
                    course_id, reg_id, first_name, last_name, learner_id)
        try:
            service.createRegistration(courseid=course_id,
                                       regid=reg_id,
                                       fname=first_name,
                                       lname=last_name,
                                       learnerid=learner_id)
        except ScormCloudError as error:
            logger.info(error)
            if error.code == 1:
                # Couldn’t find the course specified by courseid belonging to
                # appid
                raise ScormCourseNotFoundError()
            if error.code == 2:
                # Registration already exists
                pass
            if error.code == 3:
                # Postback URL login name specified without password
                raise ScormCourseNoPasswordError()


    def delete_enrollment_record(self, enrollment_record):
        reg_id = IScormIdentifier(enrollment_record).get_id()
        service = self.cloud.get_registration_service()
        logger.info("Deleting enrollment record: reg_id=%s",
                    reg_id)
        try:
            service.deleteRegistration(reg_id)
        except ScormCloudError as error:
            logger.info(error)
            raise error

    def launch(self, registration_id, redirect_url):
        service = self.cloud.get_registration_service()
        return service.launch(registration_id, redirect_url)
