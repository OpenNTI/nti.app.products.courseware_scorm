#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import hashlib

from nameparser import HumanName

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from zope import component
from zope import interface

from zope.event import notify

from nti.app.externalization.error import raise_json_error

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.courses import SCORMRegistrationIdentifier
from nti.app.products.courseware_scorm.courses import SCORMRegistrationRemovedEvent

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import IScormRegistration
from nti.app.products.courseware_scorm.interfaces import IPostBackURLUtility
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IPostBackPasswordUtility
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationReport

from nti.app.products.courseware_scorm.views import REGISTRATION_RESULT_POSTBACK_VIEW_NAME

from nti.dataserver.interfaces import ILinkExternalHrefOnly

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.users.users import User

from nti.externalization.proxy import removeAllProxies

from nti.links.links import Link
from nti.links.externalization import render_link

from nti.scorm_cloud.client import ScormCloudUtilities

from nti.scorm_cloud.client.registration import RegistrationReport

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

@interface.implementer(IPostBackURLUtility)
class PostBackURLGenerator(object):

    def url_for_registration_postback(self, enrollment, request=None):
        if request is None:
            request = get_current_request()
        link = Link(enrollment, elements=('@@'+REGISTRATION_RESULT_POSTBACK_VIEW_NAME,))
        interface.alsoProvides(link, ILinkExternalHrefOnly)
        url = render_link(link)
        return request.relative_url(url)

    
@interface.implementer(IPostBackURLUtility)
class DevModePostbackURLGenerator(PostBackURLGenerator):
    """
    An IPostbackURLUtility that logs but doesn't return the postback url.
    SCORM cloud makes a dns request at registration time to validate the provided url
    which obviously doesn't work for non public facing hosts.
    """
    def url_for_registration_postback(self, enrollment_record, request=None):
        url = super(DevModePostbackURLGenerator, self).url_for_registration_postback(enrollment_record, request=request)
        logger.debug('postback url doesnt work in devmode. %s', url)
        return None

    
_USER_SECRET = 'R9P3KouL>FQW?qjYxYQDgYDRetpMVV'
_PASS_SECRET = '6AUyRy%mRX{RcqcXwcebHTc7VtFQKa'

@interface.implementer(IPostBackPasswordUtility)
class PostBackPasswordUtility(object):
    
    def _compute_hash(self, parts):
        m = hashlib.sha256()
        for part in parts:
            m.update(part)
        return m.hexdigest()

    def _get_registration_id(self, course, user):
        identifier = component.getMultiAdapter((user, course),
                                               ISCORMIdentifier)
        return identifier.get_id()
    
    def credentials_for_enrollment(self, enrollment):
        course = enrollment.CourseInstance
        user = User.get_user(enrollment.Username)
        reg_id = self._get_registration_id(course, user)
        
        username = self._compute_hash((reg_id, _USER_SECRET))
        password = self._compute_hash((username, _PASS_SECRET))
        
        return username, password

    def validate_credentials_for_enrollment(self, enrollment, username, password):
        _user, _pass = self.credentials_for_enrollment(enrollment)
        if _user != username or _pass != password:
            raise ValueError('Bad Credentials')
        return True


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

    def import_course(self, course, source, request=None, unregister=False):
        """
        Imports a SCORM course zip file into SCORM Cloud.

        :param course: The course under which to import the SCORM course.
        :param source: The zip file source of the course to import.
        :param unregister: U users upon successful import.
        :returns: The result of the SCORM Cloud import operation.
        """
        cloud_service = self.cloud.get_course_service()
        # pylint: disable=too-many-function-args
        scorm_id = self._get_course_id(course)
        logger.info("Importing course using: app_id=%s scorm_id=%s",
                    self.app_id, scorm_id)
        metadata = ISCORMCourseMetadata(course)
        unregister = metadata.has_scorm_package() and unregister
        if scorm_id is None:
            raise_json_error(request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Uploading SCORM to a non-persistent course is forbidden."),
                             },
                             None)
        cloud_service.import_uploaded_course(scorm_id, source)
        course = removeAllProxies(course)
        interface.alsoProvides(course, ISCORMCourseInstance)

        metadata.scorm_id = scorm_id

        if unregister:
            # Unregister users. We'll rely on launching to re-register users as
            # needed.
            service = self.cloud.get_registration_service()
            registration_list = self.get_registration_list(course)
            for registration in registration_list or ():
                reg_id = registration.registration_id
                user = SCORMRegistrationIdentifier.get_user(reg_id)
                self._remove_registration(reg_id, course, user, service)
        return course

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

    def update_assets(self, course, source, request=None):
        cloud_service = self.cloud.get_course_service()
        # pylint: disable=too-many-function-args
        course_id = ISCORMIdentifier(course).get_id()
        logger.info("Updating SCORM assets using: app_id=%s course_id=%s",
                    self.app_id, course_id)
        if course_id is None:
            raise_json_error(request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Uploading SCORM to a non-persistent course is forbidden."),
                             },
                             None)
        cloud_service.update_assets(course_id, source)

    def delete_course(self, course):
        metadata = ISCORMCourseMetadata(course)
        course_id = metadata.scorm_id
        if course_id is None:
            logger.info(u"No SCORM package to delete: app_id=%s",
                        self.app_id)
            return
        try:
            logger.info(u"Deleting course using: app_id=%s, course_id=%s",
                        self.app_id, course_id)
            service = self.cloud.get_course_service()
            return service.delete_course(course_id)
        except ScormCloudError as error:
            logger.warning(error)
            if error.code == u'1':
                # This should be OK so don't raise an exception
                logger.warning(u"Couldn't find course to delete with courseid=%s",
                               course_id)
            elif error.code == u'2':
                logger.warning(u"Deleting the files associated with this course\
                               caused an internal security exception: courseid=%s",
                               course_id)
                raise error
            else:
                logger.warning(u"Unknown error occurred while deleting course:\
                               code=%s, courseid=%s",
                               error.code, course_id)
                raise error

    def sync_enrollment_record(self, enrollment_record, course):
        """
        Syncs a course enrollment record with SCORM Cloud.
        """
        # pylint: disable=too-many-function-args
        metadata = ISCORMCourseMetadata(course)
        if metadata.has_scorm_package():
            user = User.get_user(enrollment_record.Principal.id)
            reg_id = self._get_registration_id(course, user)
            self.create_registration(reg_id,
                                     user,
                                     course)

    def create_registration(self, registration_id, user, course):
        course_id = self._get_course_id(course)
        learner_id = ISCORMIdentifier(user).get_id()
        named = IFriendlyNamed(user)
        last_name = first_name = ''
        if named and named.realname:
            human_name = HumanName(named.realname)
            first_name = human_name.first
            last_name = human_name.last

        enrollment = component.getMultiAdapter((course, user), ICourseInstanceEnrollment)

        url_factory = component.getUtility(IPostBackURLUtility)
        url = url_factory.url_for_registration_postback(enrollment)
        user = None
        password = None
        if url:
            password_manager = component.getUtility(IPostBackPasswordUtility)
            user, password = password_manager.credentials_for_enrollment(enrollment)
            
        self._create_registration(course_id,
                                  registration_id,
                                  first_name,
                                  last_name,
                                  learner_id,
                                  postbackurl=url,
                                  authtype='form' if url else None,
                                  urlname=user,
                                  urlpass=password)

    def _create_registration(self, course_id, registration_id,
                             first_name, last_name, learner_id,
                             postbackurl=None, authtype=None,
                             urlname=None, urlpass=None,
                             resultsformat=None):
        logger.info("Creating SCORM registration: courseid=%s reg_id=%s fname=%s lname=%s learnerid=%s",
                    course_id, registration_id, first_name, last_name, learner_id)
        service = self.cloud.get_registration_service()
        try:
            service.createRegistration(courseid=course_id,
                                       regid=registration_id,
                                       fname=first_name,
                                       lname=last_name,
                                       learnerid=learner_id,
                                       postbackurl=postbackurl,
                                       authtype=authtype,
                                       urlname=urlname,
                                       urlpass=urlpass,
                                       resultsformat=resultsformat)
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

    def _remove_registration(self, registration_id, course, user, service=None):
        """
        Unregister the given registration ID.
        """
        if service is None:
            service = self.cloud.get_registration_service()
        logger.info("Unregistering: reg_id=%s", registration_id)
        try:
            service.deleteRegistration(registration_id)
            notify(SCORMRegistrationRemovedEvent(registration_id,
                                                 course,
                                                 user))
        except ScormCloudError as error:
            if error.code == u'1':
                logger.debug("The regid specified for deletion does not exist: %s",
                               registration_id)
            else:
                logger.warning(error)
                raise error

    def delete_enrollment_record(self, enrollment_record):
        # pylint: disable=too-many-function-args
        course = enrollment_record.CourseInstance
        metadata = ISCORMCourseMetadata(course)
        if not metadata.has_scorm_package():
            return
        user = User.get_user(enrollment_record.Principal.id)
        reg_id = self._get_registration_id(course, user)
        self._remove_registration(reg_id, course, user)

    def launch(self, course, user, redirect_url):
        service = self.cloud.get_registration_service()
        registration_id = self._get_registration_id(course, user)
        if not self.registration_exists(registration_id):
            self.create_registration(registration_id=registration_id,
                                     user=user,
                                     course=course)
        logger.info("Launching registration: regid=%s", registration_id)
        return service.launch(registration_id, redirect_url)

    def preview(self, course, redirect_url):
        course_id = self._get_course_id(course)
        service = self.cloud.get_course_service()
        return service.get_preview_url(course_id, redirect_url)

    def _get_course_id(self, course):
        return ISCORMIdentifier(course).get_id()

    def _get_registration_id(self, course, user):
        identifier = component.getMultiAdapter((user, course),
                                               ISCORMIdentifier)
        return identifier.get_id()

    def get_registration_list(self, course):
        service = self.cloud.get_registration_service()
        # pylint: disable=too-many-function-args
        course_id = self._get_course_id(course)
        reg_list = service.getRegistrationList(courseid=course_id)
        return [IScormRegistration(reg) for reg in reg_list or ()]

    def delete_all_registrations(self, course):
        service = self.cloud.get_registration_service()
        registration_list = self.get_registration_list(course)
        for registration in registration_list or ():
            service.deleteRegistration(registration.registration_id)

    def get_registration_progress(self, course, user, results_format=None):
        registration_id = self._get_registration_id(course, user)
        service = self.cloud.get_registration_service()
        try:
            result = service.get_registration_result(registration_id, results_format)
        except ScormCloudError as error:
            logger.warning(error)
            if error.code == u'1':
                # The registration specified by the given regid does not exist
                # Treat this like an existing registration with no progress
                result = RegistrationReport(format_=results_format)
            else:
                # An unexpected error occurred
                raise error
        return ISCORMRegistrationReport(result)

    def enrollment_registration_exists(self, course, user):
        registration_id = self._get_registration_id(course, user)
        return self.registration_exists(registration_id)

    def registration_exists(self, registration_id):
        service = self.cloud.get_registration_service()
        return service.exists(registration_id)

    def get_archive(self, course):
        service = self.cloud.get_course_service()
        course_id = self._get_course_id(course)
        archive = service.get_assets(course_id)
        return archive

    def get_metadata(self, course):
        service = self.cloud.get_course_service()
        # pylint: disable=too-many-function-args
        course_id = ISCORMIdentifier(course).get_id()
        return service.get_metadata(course_id)
