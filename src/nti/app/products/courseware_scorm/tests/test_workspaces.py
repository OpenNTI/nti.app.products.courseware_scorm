#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_not
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that
does_not = is_not

import fudge

from zope import component

from nti.app.products.courseware_scorm.client import SCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMWorkspace

from nti.app.products.courseware_scorm.model import ScormContentInfo

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.appserver.workspaces.interfaces import IUserService

from nti.dataserver.tests import mock_dataserver

from nti.scorm_cloud.client.course import CourseData

from nti.testing.matchers import verifiably_provides


class TestConfiguredWorkspace(CoursewareSCORMLayerTest):

    default_origin = 'http://janux.ou.edu'

    def setUp(self):
        # A non-None client for tests
        self.client = SCORMCloudClient(app_id=u'app_id',
                                      secret_key=u'secret_key',
                                      service_url=u'service_url')
        component.getGlobalSiteManager().registerUtility(self.client, ISCORMCloudClient)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.client)

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    @fudge.patch('nti.app.products.courseware_scorm.client.SCORMCloudClient.get_scorm_instances')
    def test_workspace(self, mock_content):
        """
        In the layer, with registered scorm client. We have access to the workspace.
        """
        course_data = CourseData()
        course_data.title = u'SCORM Content'
        course_data.courseId = u'123456'
        course_data.numberOfVersions = u'2'
        course_data.numberOfRegistrations = u'18'
        content_info = ScormContentInfo(course_data)
        mock_content.is_callable().returns((content_info,))

        service_url = '/dataserver2/service/'

        def _get_scorm_collection(environ=None):
            service_res = self.testapp.get(service_url,
                                           extra_environ=environ)
            service_res = service_res.json_body
            workspaces = service_res['Items']
            scorm_ws = None
            try:
                scorm_ws = next(x for x in workspaces if x['Title'] == 'SCORM')
            except StopIteration:
                pass
            assert_that(scorm_ws, not_none())
            try:
                scorm_collection = next(x for x in scorm_ws['Items']
                                         if x['Title'] == 'SCORMInstances')
            except StopIteration:
                pass
            assert_that(scorm_collection, not_none())
            return scorm_collection

        # Admin
        scorm_collection = _get_scorm_collection()
        scorm_collection_href = scorm_collection['href']

        # No site means our scorm content is filtered out
        scorm_res = self.testapp.get(scorm_collection_href)
        scorm_res = scorm_res.json_body
        scorm_items = scorm_res.get('Items')
        assert_that(scorm_items, has_length(0))

        # Incorrect site is filtered out
        course_data.tags = ('alpha.nextthought.com',)
        content_info = ScormContentInfo(course_data)
        mock_content.is_callable().returns((content_info,))
        scorm_res = self.testapp.get(scorm_collection_href)
        scorm_res = scorm_res.json_body
        scorm_items = scorm_res.get('Items')
        assert_that(scorm_items, has_length(0))

        # Filter lines up
        course_data.tags = ('janux.ou.edu',)
        content_info = ScormContentInfo(course_data)
        mock_content.is_callable().returns((content_info,))
        scorm_res = self.testapp.get(scorm_collection_href)
        scorm_res = scorm_res.json_body
        scorm_items = scorm_res.get('Items')
        assert_that(scorm_items, has_length(1))
        report = scorm_items[0]
        assert_that(report, has_entries('title', u'SCORM Content',
                                        'scorm_id', u'123456',
                                        'course_version', u'2',
                                        'registration_count', 18))


class TestUnconfiguredWorkspace(ApplicationLayerTest):

    testapp = None

    @WithSharedApplicationMockDS
    def test_workspace(self):
        """
        With no registered scorm client, this workspace is not available.
        """
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user()
            service = IUserService(user)

            workspaces = service.workspaces

            assert_that(workspaces,
                        does_not(has_item(verifiably_provides(ISCORMWorkspace))))
