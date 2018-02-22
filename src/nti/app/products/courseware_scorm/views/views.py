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

from zope import component

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.views import SCORM_PROGRESS_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import is_course_editor
from nti.contenttypes.courses.utils import is_course_instructor
from nti.contenttypes.courses.utils import get_enrollment_record

from nti.dataserver import authorization as nauth

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             name=LAUNCH_SCORM_COURSE_VIEW_NAME)
class LaunchSCORMCourseView(AbstractAuthenticatedView):
    """
    A view for launching a course on SCORM Cloud.
    """

    def __call__(self):
        if      get_enrollment_record(self.context, self.remoteUser) is None \
            and not is_course_editor(self.context, self.remoteUser) \
            and not is_course_instructor(self.context, self.remoteUser) \
            and not nauth.is_admin_or_site_admin(self.remoteUser):
            return hexc.HTTPForbidden(_(u"You do not have access to this SCORM content."))
        redirect_url = CaseInsensitiveDict(self.request.params).get(u'redirecturl',
                                                                    u'message')
        client = component.getUtility(ISCORMCloudClient)
        launch_url = client.launch(self.context, self.remoteUser, redirect_url)
        return hexc.HTTPSeeOther(location=launch_url)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             name=SCORM_PROGRESS_VIEW_NAME)
class SCORMProgressView(AbstractAuthenticatedView):
    """
    A view for observing SCORM registration progress.
    """

    def __call__(self):
        if      get_enrollment_record(self.context, self.remoteUser) is None \
            and not is_course_editor(self.context, self.remoteUser) \
            and not is_course_instructor(self.context, self.remoteUser) \
            and not nauth.is_admin_or_site_admin(self.remoteUser):
            return hexc.HTTPForbidden(_(u"You do not have access to this SCORM content."))
        client = component.getUtility(ISCORMCloudClient)
        return client.get_registration_progress(self.context, self.remoteUser)
