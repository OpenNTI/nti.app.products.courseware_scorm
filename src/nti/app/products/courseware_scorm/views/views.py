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

from xml.dom import minidom

from xml.parsers.expat import ExpatError

from zope import component
from zope import interface

from zope.event import notify

from nti.app.base.abstract_views import AbstractView
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationReport
from nti.app.products.courseware_scorm.interfaces import IPostBackPasswordUtility
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.app.products.courseware_scorm.views import SCORM_PROGRESS_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import PREVIEW_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import REGISTRATION_RESULT_POSTBACK_VIEW_NAME

from nti.contenttypes.completion.interfaces import UserProgressUpdatedEvent

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import is_course_instructor_or_editor

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.dataserver.users.users import User 

from nti.scorm_cloud.client.registration import RegistrationReport

logger = __import__('logging').getLogger(__name__)



class AbstractSCORMLaunchView(AbstractAuthenticatedView):

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

    def _before_launch(self):
        pass

    def __call__(self):
        try:
            self._before_launch()
            redirect_url = self._redirect_uri()
            launch_url = self._build_launch_url(redirect_url)
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
             name=PREVIEW_SCORM_COURSE_VIEW_NAME)
class PreviewSCORMCourseVIew(AbstractSCORMLaunchView):
    """
    A view for previewing a course on SCORM Cloud.
    """

    def _build_launch_url(self, redirect_url):
        client = component.getUtility(ISCORMCloudClient)
        return client.preview(self.context, redirect_url or u'message')

    def _before_launch(self):
        if not is_admin_or_content_admin_or_site_admin(self.remoteUser) \
           and not is_course_instructor_or_editor(self.context, self.remoteUser):
            raise hexc.HTTPForbidden()
        

@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=ACT_READ,
             name=LAUNCH_SCORM_COURSE_VIEW_NAME)
class LaunchSCORMCourseView(AbstractSCORMLaunchView):
    """
    A view for launching a course on SCORM Cloud.
    """

    def _build_launch_url(self, redirect_url):
        client = component.getUtility(ISCORMCloudClient)
        return client.launch(self.context, self.remoteUser, redirect_url or u'message')
    
@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstanceEnrollment,
             request_method='GET',
             permission=ACT_READ,
             name=SCORM_PROGRESS_VIEW_NAME)
class SCORMProgressView(AbstractAuthenticatedView):
    """
    A view for observing SCORM registration progress.
    """
    
    def _results_format(self):
        return CaseInsensitiveDict(self.request.params).get(u'resultsFormat')

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        user = User.get_user(self.context.Username) 
        return client.get_registration_progress(self.context.CourseInstance, user, self._results_format())


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstanceEnrollment,
             request_method='POST',
             name=REGISTRATION_RESULT_POSTBACK_VIEW_NAME)
class SCORMRegistrationResultPostBack(AbstractView):

    def __call__(self):
        username = self.request.params.get('username', None)
        password = self.request.params.get('password', None)
        data = self.request.params.get('data', None)

        if not username or not password or not data:
            raise hexc.HTTPBadRequest()

        password_manager = component.getUtility(IPostBackPasswordUtility)
        try:
            password_manager.validate_credentials_for_enrollment(self.context, username, password)
        except ValueError:
            raise hexc.HTTPForbidden()

        # Parse the data and store completion information on the course
        try:
            xmldoc = minidom.parseString(data)
        except (UnicodeEncodeError, ExpatError) as error:
            logger.exception(u"Postback data cannot be parsed into XML: %s", error)
            return hexc.HTTPUnprocessableEntity()
        
        nodes = xmldoc.getElementsByTagName('registrationreport')
        report = RegistrationReport.fromMinidom(nodes[0]) if nodes else None
        if report is None:
            logger.info(u"Postback XML cannot be parsed into RegistrationReport")
            return hexc.HTTPUnprocessableEntity()
        report = ISCORMRegistrationReport(report)
        
        user = User.get_user(self.context.Username)
        course = self.context.CourseInstance
        registration_id = self._get_registration_id(course, user)
        if registration_id != report.registration_id:
            logger.info(u"Postback regid (%s) does not match enrollment regid (%s)",
                        report.registration_id, registration_id)
            return hexc.HTTPBadRequest()
        metadata = ISCORMCourseMetadata(course)
        container = IUserRegistrationReportContainer(metadata)
        container.add_registration_report(report, user)
        notify(UserProgressUpdatedEvent(obj=metadata,
                                        user=user,
                                        context=course))
        
        logger.info(u"Registration report postback stored: user=%s", user.username)

        return hexc.HTTPNoContent()
    
    def _get_registration_id(self, course, user):
        identifier = component.getMultiAdapter((user, course),
                                               ISCORMIdentifier)
        return identifier.get_id()
        
