#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from six.moves import urllib_parse

from zope import component

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.views import SCORM_PROGRESS_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.authorization import ACT_READ

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=ACT_READ,
             name=LAUNCH_SCORM_COURSE_VIEW_NAME)
class LaunchSCORMCourseView(AbstractAuthenticatedView):
    """
    A view for launching a course on SCORM Cloud.
    """

    def _redirect_uri(self):
        return CaseInsensitiveDict(self.request.params).get(u'redirecturl')

    def _redirect_on_error(self, redirect_url, e):
        if not redirect_url:
            return None

        # Be really careful here that we don't clobber
        # query params that may have been provided
        url_parts = list(urllib_parse.urlparse(redirect_url))
        query = dict(urllib_parse.parse_qsl(url_parts[4]))
        query.update({"error": str(e)})

        url_parts[4] = urllib_parse.urlencode(query)
        return urllib_parse.urlunparse(url_parts)

    def __call__(self):
        try:
            redirect_url = self._redirect_uri()
            client = component.getUtility(ISCORMCloudClient)
            launch_url = client.launch(self.context, self.remoteUser, redirect_url or u'message')
        except Exception as e:
            logger.exception('Unable to generate scorm cloud launch url')
            # This is a fairly wide catch but this view is intended to be browser rendered
            # so if we get an error we can detect send them back to the redirect with an error
            # param.  If they didn't pass a redirect_url just reraise
            on_error_redirect = self._redirect_on_error(redirect_url, e)
            if on_error_redirect:
                return hexc.HTTPSeeOther(location=on_error_redirect)
            raise
        return hexc.HTTPSeeOther(location=launch_url)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=ACT_READ,
             name=SCORM_PROGRESS_VIEW_NAME)
class SCORMProgressView(AbstractAuthenticatedView):
    """
    A view for observing SCORM registration progress.
    """

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        return client.get_registration_progress(self.context, self.remoteUser)
