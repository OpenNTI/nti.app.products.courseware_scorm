#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import instance_of
from hamcrest import has_properties
from hamcrest import has_entries
from hamcrest import has_key
does_not = is_not

from nti.testing.matchers import provides

from persistent import Persistent

from zope import component
from zope import interface

from nti.app.products.courseware_scorm.client import SCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.tests import SCORMLayerTest

from nti.externalization import new_from_external_object
from nti.externalization import to_external_object

from nti.scorm_cloud.client import ScormCloudService

from nti.scorm_cloud.interfaces import IScormCloudService


@interface.implementer(IScormCloudService)
class MockSCORMCloudService(ScormCloudService):
    """
    A mock SCORM Cloud service used for testing.
    """


class TestClient(SCORMLayerTest):

    def setUp(self):
        # A non-None client for tests
        self.client = SCORMCloudClient(app_id=u'app_id',
                                      secret_key=u'secret_key',
                                      service_url=u'service_url')
        component.getGlobalSiteManager().registerUtility(self.client, ISCORMCloudClient)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.client, ISCORMCloudClient)

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

    def test_to_external(self):
        ext = to_external_object(self.client)
        assert_that(ext, does_not(has_key('secret_key')))
        assert_that(ext, has_entries('MimeType', 'application/vnd.nextthought.scorm.scormcloudclient',
                                     'app_id', 'app_id',
                                     'service_url', 'service_url'))

class TestPersistentClient(SCORMLayerTest):

    def test_from_external(self):
        external = {
            'MimeType': 'application/vnd.nextthought.scorm.scormcloudclient',
            'app_id': 'myapp',
            'secret_key': 'mysecret'
        }
        client = new_from_external_object(external)
        assert_that(client, provides(ISCORMCloudClient))
        assert_that(client, instance_of(Persistent))

        assert_that(client, has_properties('app_id', 'myapp',
                                           'secret_key', 'mysecret'))

    def test_to_external(self):
        external = {
            'MimeType': 'application/vnd.nextthought.scorm.scormcloudclient',
            'app_id': 'myapp',
            'secret_key': 'mysecret'
        }
        client = new_from_external_object(external)
        ext = to_external_object(client)
        assert_that(ext, does_not(has_key('secret_key')))
        assert_that(ext, has_entries('MimeType', 'application/vnd.nextthought.scorm.scormcloudclient',
                                     'app_id', 'myapp',
                                     'service_url', 'https://cloud.scorm.com/EngineWebServices'))
