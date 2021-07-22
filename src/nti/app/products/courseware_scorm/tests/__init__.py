#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from zope import component

import zope.testing.cleanup

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.app.products.courseware_scorm.client import SCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.testing.base import AbstractTestBase

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.app.products.courseware_scorm',)

    @classmethod
    def setUp(cls):
        cls.setUpPackages()
        # A non-None client for tests
        cls.client = SCORMCloudClient(app_id=u'app_id',
                                      secret_key=u'secret_key',
                                      service_url=u'http://example.com/service_url')
        component.getGlobalSiteManager().registerUtility(cls.client, ISCORMCloudClient)

    @classmethod
    def tearDown(cls):
        component.getGlobalSiteManager().unregisterUtility(cls.client, ISCORMCloudClient)
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        test = test or find_test()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass


class SCORMLayerTest(ApplicationLayerTest):

    layer = SharedConfiguringTestLayer


class CoursewareSCORMLayerTest(ApplicationLayerTest):

    layer = PersistentInstructedCourseApplicationTestLayer

    get_configuration_package = AbstractTestBase.get_configuration_package.__func__

    set_up_packages = ('nti.app.products.courseware_scorm',)

