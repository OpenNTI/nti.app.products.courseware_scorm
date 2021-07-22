#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_entries
from hamcrest import has_key
does_not = is_not

from zope import component

from nti.app.products.courseware_scorm.client import SCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.tests import SCORMApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

logger = __import__('logging').getLogger(__name__)

class TestSCORMClientManagement(SCORMApplicationLayerTest):

    default_origin = 'http://janux.ou.edu'
    management_view = '/dataserver2/++etc++hostsites/janux.ou.edu/@@ScormCloudClient'

    def setUp(self):
        # A non-None client for tests
        self.client = SCORMCloudClient(app_id=u'app_id',
                                      secret_key=u'secret_key',
                                      service_url=u'service_url')
        component.getGlobalSiteManager().registerUtility(self.client, ISCORMCloudClient)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.client)

    @WithSharedApplicationMockDS(testapp=True, users=['learner'])
    def test_get_configured_client(self):
        # Note that our setup creates a globally registered utility

        admin_environ = self._make_extra_environ(self.default_username)
        learner_environ = self._make_extra_environ('learner')

        # You have to be a nti admin
        self.testapp.get(self.management_view,
                         status=403,
                         extra_environ=learner_environ)

        resp = self.testapp.get(self.management_view,
                                status=200,
                                extra_environ=admin_environ)
        resp = resp.json

        assert_that(resp, has_entries('app_id', 'app_id',
                                      'service_url', 'service_url'))
        # the secret is stripped
        assert_that(resp, does_not(has_key('secret_key')))
        

        # Our test setup registers a client globally, but if there isn't a client
        # configured you get a 404
        component.getGlobalSiteManager().unregisterUtility(self.client)

        self.testapp.get(self.management_view,
                         status=404,
                         extra_environ=admin_environ)

    @WithSharedApplicationMockDS(testapp=True, users=['learner'])
    def test_manage_overrides(self):
        # Note that our setup creates a globally registered utility

        admin_environ = self._make_extra_environ(self.default_username)
        learner_environ = self._make_extra_environ('learner')

        incoming = {
            'MimeType': 'application/vnd.nextthought.scorm.scormcloudclient',
            'app_id': 'foo',
            'secret_key':'secret'
        }

        # We can set configuration for a site by posting data to the management
        # view. We can only do this as an admin
        self.testapp.post_json(self.management_view,
                               incoming,
                               status=403,
                               extra_environ=learner_environ)

        self.testapp.post_json(self.management_view,
                               incoming,
                               status=201,
                               extra_environ=admin_environ)

        # And now fetching it we see our overridden values
        resp = self.testapp.get(self.management_view,
                                status=200,
                                extra_environ=admin_environ)
        resp = resp.json

        assert_that(resp, has_entries('app_id', 'foo'))
        
        # But once we have set one persistently we can't set another one
        incoming['app_id'] = 'bar'
        self.testapp.post_json(self.management_view,
                               incoming,
                               status=409,
                               extra_environ=admin_environ)

        # NTI Admins can delete site overrides also
        self.testapp.delete(self.management_view,
                               status=403,
                               extra_environ=learner_environ)
        
        self.testapp.delete(self.management_view,
                               status=204,
                               extra_environ=admin_environ)

        # Which causes the override to stop coming back

        resp = self.testapp.get(self.management_view,
                                status=200,
                                extra_environ=admin_environ)
        resp = resp.json

        assert_that(resp, has_entries('app_id', 'app_id',
                                      'service_url', 'service_url'))
