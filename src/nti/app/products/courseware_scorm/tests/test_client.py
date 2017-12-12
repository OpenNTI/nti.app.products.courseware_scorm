#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

from zope import component
from zope import interface

from nti.scorm_cloud.interfaces import IScormCloudService
from nti.scorm_cloud.interfaces import IDebugService
from nti.scorm_cloud.interfaces import IRegistrationService
from nti.scorm_cloud.interfaces import IInvitationService
from nti.scorm_cloud.interfaces import IUploadService
from nti.scorm_cloud.interfaces import ICourseService
from nti.scorm_cloud.interfaces import IReportingService

from nti.scorm_cloud.client import ScormCloudService
from nti.scorm_cloud.client import ScormCloudUtilities
from nti.scorm_cloud.client.config import Configuration

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

#FIXME: 'MockSCORMCloudService' object has no attribute 'withargs'
@interface.implementer(IScormCloudService)
class MockSCORMCloudService(object):
    """
    A mock SCORM Cloud service used for testing.
    """

    def __init__(self, configuration):
        self.config = configuration

    @classmethod
    def withconfig(cls, config):
        """
        Named constructor that creates a ScormCloudService with the specified
        Configuration object.

        Arguments:
        config -- the Configuration object holding the required configuration
            values for the SCORM Cloud API
        """
        return cls(config)

    @classmethod
    def withargs(cls, appid, secret, serviceurl,
                 origin='rusticisoftware.pythonlibrary.2.0.0'):
        """
        Named constructor that creates a ScormCloudService with the specified
        configuration values.

        Arguments:
        appid -- the AppID for the application defined in the SCORM Cloud
            account
        secret -- the secret key for the application
        serviceurl -- the service URL for the SCORM Cloud web service. For
            example, http://cloud.scorm.com/EngineWebServices
        origin -- the origin string for the application software using the
            API/Python client library
        """
        return cls(Configuration(appid, secret, serviceurl, origin))

    def get_course_service():
        """
        Retrieves the CourseService.

        :return: return a new course service object
        :rtype: :class:`.ICourseService`
        """

    def get_debug_service():
        """
        Retrieves the DebugService.

        :return: return a new debug service object
        :rtype: :class:`.IDebugService`
        """

    def get_registration_service():
        """
        Retrieves the RegistrationService.

        :return: return a new registration service object
        :rtype: :class:`.IRegistrationService`
        """

    def get_invitation_service():
        """
        Retrieves the InvitationService.

        :return: return a new invitation service object
        :rtype: :class:`.IInvitationService`
        """

    def get_reporting_service():
        """
        Retrieves the ReportingService.

        :return: return a new reporting service object
        :rtype: :class:`.IReportingService`
        """

    def get_upload_service():
        """
        Retrieves the UploadService.

        :return: return a new upload service object
        :rtype: :class:`.IUploadService`
        """


class TestClient(CoursewareSCORMLayerTest):

    def test_client(self):
        service = component.getUtility(IScormCloudService)
        assert_that(service, is_not(none()))
        client = component.getUtility(ISCORMCloudClient)
        assert_that(client, is_not(none()))

    def test_upload_course(self):
        import_url = 'https://scorm.com/wp-content/assets/golf_examples/PIFS/RuntimeBasicCalls_SCORM20043rdEdition.zip'
        service = component.getUtility(IScormCloudService)
        assert_that(service, is_not(none()))
        # assert_that(upload_service, is_not(none()))
        # cloud_upload_link = upload_service.get_upload_url(import_url)
        # assert_that(cloud_upload_link, is_not(none()))
