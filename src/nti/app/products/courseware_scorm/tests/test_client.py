#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

from zope import component

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest


class TestClient(CoursewareSCORMLayerTest):

    def test_client(self):
        client = component.getUtility(ISCORMCloudClient)
        assert_that(client, is_not(none()))
