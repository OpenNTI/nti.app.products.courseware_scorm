#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

import unittest

from zope import component

from zope.component.hooks import setHooks

from zope.configuration import config
from zope.configuration import xmlconfig

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.testing.base import AbstractTestBase

# Example ZCML file that would call the registerSCORMCloudClient directive
HEAD_ZCML_STRING = u"""
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:scorm="http://nextthought.com/ntp/scorm">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="zope.security" />
    <include package="." file="meta.zcml"/>

    <configure>
        <scorm:registerSCORMCloudService
            factory=".tests.test_client.MockSCORMCloudService" />
        <scorm:registerSCORMCloudClient
			app_id="AQYJPZXZAY"
			secret_key="G9M1J6uv1hr3ll7wnkPWGFXutMqQXbdhXX8dZnE8"
 			service_url="https://cloud.scorm.com/EngineWebServices" />
    </configure>
</configure>
"""


class TestZcml(unittest.TestCase):

    get_config_package = AbstractTestBase.get_configuration_package.__func__

    def setUp(self):
        super(TestZcml, self).setUp()
        setHooks()

    def test_zcml(self):
        # Using the above ZCML string, set up the temporary configuration and run the string
        # through ZCML processor
        context = config.ConfigurationMachine()
        context.package = self.get_config_package()
        xmlconfig.registerCommonDirectives(context)
        xmlconfig.string(HEAD_ZCML_STRING, context)

        client = component.getUtility(ISCORMCloudClient)
        assert_that(client, is_not(none()))
