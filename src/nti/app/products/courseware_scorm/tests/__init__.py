#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

import zope.testing.cleanup


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.app.products.courseware_scorm',)

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        test = test or find_test()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass


import unittest


class CoursewareSCORMLayerTest(unittest.TestCase):

    layer = SharedConfiguringTestLayer


class CoursewareSCORMTestLayer(PersistentInstructedCourseApplicationTestLayer):

    set_up_packages = ('nti.dataserver', 'nti.app.products.courseware_scorm')

    @classmethod
    def setUp(cls):
        PersistentInstructedCourseApplicationTestLayer.setUp()
        # We need to use configure_packages instead of setUpPackages
        # to avoid having zope.eventtesting.events.append duplicated
        # as a handler. This is poorly documented in nti.testing 1.0.0.
        # Passing in our context is critical.
        cls.configure_packages(set_up_packages=cls.set_up_packages,
                               features=cls.features,
                               context=cls.configuration_context)

    @classmethod
    def testSetUp(cls):
        pass
