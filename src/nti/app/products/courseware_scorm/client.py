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

from nti.app.products.courseware_scorm.courses import is_course_admin

from nti.app.products.courseware_scorm.interfaces import ISCORMProgress
from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import IScormRegistration
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.contenttypes.courses.utils import get_enrollment_record

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

    def __init__(self, app_id, secret_key, service_url):
        self.app_id = app_id
        self.secret_key = secret_key
        origin = ScormCloudUtilities.get_canonical_origin_string('NextThought',
                                                                 'Platform', '1.0')
        service = component.getUtility(IScormCloudService)
        self.cloud = service.withargs(app_id, secret_key, service_url, origin)

    def import_course(self, context, source, request=None):
        """
        Imports a SCORM course zip file into SCORM Cloud.

        :param context: The course context under which to import the SCORM course.
        :param source: The zip file source of the course to import.
        :returns: The result of the SCORM Cloud import operation.
        """
        cloud_service = self.cloud.get_course_service()
        # pylint: disable=too-many-function-args
        scorm_id = ISCORMIdentifier(context).get_id()
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
        user = User.get_user(enrollment_record.Principal.id)
        reg_id = self._get_registration_id(course, user)
        self.create_registration(reg_id,
                                 user,
                                 course)

    def create_registration(self, registration_id, user, course):
        course_id = ISCORMIdentifier(course).get_id()
        learner_id = ISCORMIdentifier(user).get_id()
        named = IFriendlyNamed(user)
        last_name = first_name = ''
        if named and named.realname:
            human_name = HumanName(named.realname)
            first_name = human_name.first
            last_name = human_name.last
        self._create_registration(course_id,
                                  registration_id,
                                  first_name,
                                  last_name,
                                  learner_id)

    def _create_registration(self, course_id, registration_id,
                             first_name, last_name, learner_id):
        logger.info("Creating SCORM registration: courseid=%s reg_id=%s fname=%s lname=%s learnerid=%s",
                    course_id, registration_id, first_name, last_name, learner_id)
        service = self.cloud.get_registration_service()
        try:
            service.createRegistration(courseid=course_id,
                                       regid=registration_id,
                                       fname=first_name,
                                       lname=last_name,
                                       learnerid=learner_id)
        except ScormCloudError as error:
            logger.warning(error)
            if error.code == u'1':
                # Couldn’t find the course specified by courseid belonging to
                # appid
                raise ScormCourseNotFoundError()
            elif error.code == u'2':
                logger.warning("Registration already exists for course %s",
                               course_id)
            elif error.code == u'3':
                # Postback URL login name specified without password
                raise ScormCourseNoPasswordError()
            else:
                raise error

    def delete_enrollment_record(self, enrollment_record):
        # pylint: disable=too-many-function-args
        course = enrollment_record.CourseInstance
        user = User.get_user(enrollment_record.Principal.id)
        reg_id = self._get_registration_id(course, user)
        service = self.cloud.get_registration_service()
        logger.info("Deleting enrollment record: reg_id=%s",
                    reg_id)
        try:
            service.deleteRegistration(reg_id)
        except ScormCloudError as error:
            logger.warning(error)
            if error.code == u'1':
                # The registration specified by regid does not exist
                logger.warning("The regid specified for deletion does not exist: %s",
                               reg_id)
            else:
                raise error

    def launch(self, course, user, redirect_url):
        service = self.cloud.get_registration_service()
        registration_id = self._get_registration_id(course, user)
        if      is_course_admin(user, course) \
            and not self.registration_exists(registration_id):
            course_id = ISCORMIdentifier(course).get_id()
            self.create_registration(registration_id=registration_id,
                                     user=user,
                                     course=course)
        return service.launch(registration_id, redirect_url)

    def _get_registration_id(self, course, user):
        identifier = component.getMultiAdapter((user, course), ISCORMIdentifier)
        return identifier.get_id()

    def get_registration_list(self, course):
        service = self.cloud.get_registration_service()
        # pylint: disable=too-many-function-args
        course_id = ISCORMIdentifier(course).get_id()
        reg_list = service.getRegistrationList(courseid=course_id)
        return [IScormRegistration(reg) for reg in reg_list or ()]

    def delete_all_registrations(self, course):
        service = self.cloud.get_registration_service()
        registration_list = self.get_registration_list(course)
        for registration in registration_list or ():
            service.deleteRegistration(registration.registrationId)

    def get_registration_progress(self, course, user):
        registration_id = self._get_registration_id(course, user)
        service = self.cloud.get_registration_service()
        return ISCORMProgress(service.get_registration_result(registration_id))

    def registration_exists(self, registration_id):
        service = self.cloud.get_registration_service()
        return service.exists(registration_id)

    def get_archive(self, course):
        service = self.cloud.get_course_service()
        course_id = IScormIdentifier(course).get_id()
        archive = service.get_assets(course_id)
        return archive

    def get_metadata(self, course):
        service = self.cloud.get_course_service()
        course_id = IScormIdentifier(course).get_id()
        return service.get_metadata(course_id)
