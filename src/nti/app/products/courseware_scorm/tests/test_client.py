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

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.scorm_cloud.client.config import Configuration

from nti.scorm_cloud.interfaces import IScormCloudService


@interface.implementer(IScormCloudService)
class MockSCORMCloudService(object):
    """
    A mock SCORM Cloud service used for testing.
    """

    def __init__(self, configuration):
        self.config = configuration

    @classmethod
    def withconfig(cls, config):
        return cls(config)

    @classmethod
    def withargs(cls, appid, secret, serviceurl,
                 origin='rusticisoftware.pythonlibrary.2.0.0'):
        return cls(Configuration(appid, secret, serviceurl, origin))

    def get_course_service(self):
        pass

    def get_debug_service(self):
        pass

    def get_registration_service(self):
        pass

    def get_invitation_service(self):
        pass

    def get_reporting_service(self):
        pass

    def get_upload_service(self):
        pass


class TestClient(CoursewareSCORMLayerTest):

    def test_client(self):
        service = component.getUtility(IScormCloudService)
        assert_that(service, is_not(none()))
        client = component.getUtility(ISCORMCloudClient)
        assert_that(client, is_not(none()))

    def test_upload_course(self):
        # import_url = 'https://scorm.com/wp-content/assets/golf_examples/PIFS/RuntimeBasicCalls_SCORM20043rdEdition.zip'
        service = component.getUtility(IScormCloudService)
        assert_that(service, is_not(none()))
        # assert_that(upload_service, is_not(none()))
        # cloud_upload_link = upload_service.get_upload_url(import_url)
        # assert_that(cloud_upload_link, is_not(none()))
