#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from six.moves import urllib_parse

from xml.dom import minidom

from xml.parsers.expat import ExpatError

from zope import component

from zope.event import notify

from nti.app.base.abstract_views import AbstractView
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_scorm.courses import UserRegistrationReportContainer

from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import SCORMPackageLaunchEvent
from nti.app.products.courseware_scorm.interfaces import IPostBackPasswordUtility
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationReport
from nti.app.products.courseware_scorm.interfaces import IRegistrationReportContainer
from nti.app.products.courseware_scorm.interfaces import SCORMRegistrationPostbackEvent

from nti.app.products.courseware_scorm.utils import get_scorm_refs
from nti.app.products.courseware_scorm.utils import parse_registration_id
from nti.app.products.courseware_scorm.utils import get_registration_id_for_user_and_course

from nti.app.products.courseware_scorm.views import SCORM_PROGRESS_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import PREVIEW_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import REGISTRATION_RESULT_POSTBACK_VIEW_NAME

from nti.contenttypes.completion.interfaces import UserProgressUpdatedEvent

from nti.contenttypes.completion.utils import get_completed_item

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import is_course_instructor_or_editor

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.dataserver.users.users import User

from nti.scorm_cloud.client.registration import RegistrationReport

from nti.traversal.traversal import find_interface

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

    def _after_launch(self):
        pass

    def _get_scorm_id(self):
        pass

    def __call__(self):
        scorm_id = self._get_scorm_id()
        try:
            self._before_launch()
            redirect_url = self._redirect_uri()
            launch_url = self._build_launch_url(scorm_id, redirect_url)
        except Exception as e:
            logger.exception('Unable to generate scorm cloud launch url')
            # This is a fairly wide catch but this view is intended to be browser rendered
            # so if we get an error we can detect send them back to the redirect with an error
            # param.  If they didn't pass a redirect_url just reraise
            on_error_redirect = self._redirect_on_error(redirect_url, e)
            if on_error_redirect:
                return hexc.HTTPSeeOther(location=on_error_redirect)
            raise
        self._after_launch()
        return hexc.HTTPSeeOther(location=launch_url)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=ACT_READ,
             name=PREVIEW_SCORM_COURSE_VIEW_NAME)
class PreviewSCORMCourseView(AbstractSCORMLaunchView):
    """
    A view for previewing a course on SCORM Cloud.
    """

    def _get_scorm_id(self):
        metadata = ISCORMCourseMetadata(self.context, None)
        scorm_id = getattr(metadata, 'scorm_id', None)
        if not scorm_id:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"No metadata scorm_id associated with course."),
                                 'code': u'NoScormIdFoundError'
                             },
                             None)
        return scorm_id

    def _build_launch_url(self, scorm_id, redirect_url):
        client = component.getUtility(ISCORMCloudClient)
        return client.preview(scorm_id, redirect_url or u'message')

    def _before_launch(self):
        if     not is_admin_or_content_admin_or_site_admin(self.remoteUser) \
           and not is_course_instructor_or_editor(self.context, self.remoteUser):
            raise hexc.HTTPForbidden()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMContentRef,
             request_method='GET',
             permission=ACT_READ,
             name=PREVIEW_SCORM_COURSE_VIEW_NAME)
class PreviewSCORMContentView(PreviewSCORMCourseView):
    """
    A view for previewing scorm content.
    """

    def _get_scorm_id(self):
        return self.context.scorm_id

    def _before_launch(self):
        course = find_interface(self.context, ICourseInstance)
        if     not is_admin_or_content_admin_or_site_admin(self.remoteUser) \
           and not is_course_instructor_or_editor(course, self.remoteUser):
            raise hexc.HTTPForbidden()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=ACT_READ,
             name=LAUNCH_SCORM_COURSE_VIEW_NAME)
class LaunchSCORMCourseView(PreviewSCORMCourseView):
    """
    A view for launching a course on SCORM Cloud.
    """

    def _before_launch(self):
        pass

    def _build_launch_url(self, scorm_id, redirect_url):
        client = component.getUtility(ISCORMCloudClient)
        return client.launch(scorm_id, self.context,
                             self.remoteUser, redirect_url or u'message')

    def _after_launch(self):
        metadata = ISCORMCourseMetadata(self.context)
        notify(SCORMPackageLaunchEvent(self.remoteUser, self.context,
                                       metadata, datetime.utcnow()))
        # Make sure we commit our job
        self.request.environ['nti.request_had_transaction_side_effects'] = True


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMContentRef,
             request_method='GET',
             permission=ACT_READ,
             name=LAUNCH_SCORM_COURSE_VIEW_NAME)
class LaunchSCORMContentView(LaunchSCORMCourseView):
    """
    A view for launching a course on SCORM Cloud.
    """

    def _get_scorm_id(self):
        return self.context.scorm_id

    def _build_launch_url(self, scorm_id, redirect_url):
        course = find_interface(self.context, ICourseInstance)
        client = component.getUtility(ISCORMCloudClient)
        return client.launch(scorm_id, course,
                             self.remoteUser, redirect_url or u'message')

    def _after_launch(self):
        course = find_interface(self.context, ICourseInstance)
        notify(SCORMPackageLaunchEvent(self.remoteUser, course,
                                       self.context, datetime.utcnow()))
        # Make sure we commit our job
        self.request.environ['nti.request_had_transaction_side_effects'] = True


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
        course = self.context.CourseInstance
        metadata = ISCORMCourseMetadata(course, None)
        if metadata is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"No metadata scorm_id associated with course."),
                                 'code': u'NoScormIdFoundError'
                             },
                             None)
        registration_id = get_registration_id_for_user_and_course(metadata.scorm_id,
                                                                  user,
                                                                  course)
        return client.get_registration_progress(registration_id,
                                                self._results_format())


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMContentRef,
             request_method='GET',
             permission=ACT_READ,
             name=SCORM_PROGRESS_VIEW_NAME)
class SCORMContentProgressView(SCORMProgressView):
    """
    A view for observing SCORM content registration progress.
    """

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        course = find_interface(self.context, ICourseInstance)
        registration_id = get_registration_id_for_user_and_course(self.context.scorm_id,
                                                                  self.remoteUser,
                                                                  course)
        return client.get_registration_progress(registration_id,
                                                self._results_format())



@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstanceEnrollment,
             request_method='POST',
             name=REGISTRATION_RESULT_POSTBACK_VIEW_NAME)
class SCORMRegistrationResultPostBack(AbstractView):
    """
    The postback view we take scorm cloud to via the :class:`IPostBackURLUtility`.

    We can get the course and user via the context, and the scorm id via parsing
    the registration id (i.e. <enrollment-ds-intid>_<scorm-id>) in the payload.
    """

    def process(self, scorm_id, user, course, user_container, report):
        """
        Send events for the completable items as having progress updated. This
        will include scorm metadata or scorm content refs. If many refs point
        the same scorm_id, each will have progress/completion based on the
        registration report in this view's payload.
        """
        if ISCORMCourseInstance.providedBy(course):
            scorm_meta = ISCORMCourseMetadata(course)
            scorm_content = (scorm_meta,)
        else:
            # Ok, get all valid scorm content refs for our scorm_id
            scorm_content = get_scorm_refs(course, scorm_id)

        has_sucessfully_completed = False
        for scorm_content in scorm_content:
            if not has_sucessfully_completed:
                # Only need one indication that a previous report has marked
                # the user as successfully completing this scorm_id.
                completed_item = get_completed_item(user, course, scorm_content)
                if completed_item is not None and completed_item.Success:
                    has_sucessfully_completed = True
            # We still broadcast the events in any case.
            notify(UserProgressUpdatedEvent(obj=scorm_content,
                                            user=user,
                                            context=course))
            notify(SCORMRegistrationPostbackEvent(user, course, scorm_content, datetime.utcnow()))

        prev_report = user_container.get_registration_report(scorm_id)
        if prev_report is None:
            # First report for this scorm id
            user_container.add_registration_report(scorm_id, report)
        elif not has_sucessfully_completed:
            # Not the first report, but the previous report did not indicate
            # completion for this scorm id.
            user_container.remove_registration_report(scorm_id)
            user_container.add_registration_report(scorm_id, report)

    def __call__(self):
        username = self.request.params.get('username', None)
        password = self.request.params.get('password', None)
        data = self.request.params.get('data', None)

        if not username or not password or not data:
            raise hexc.HTTPBadRequest()

        password_manager = component.getUtility(IPostBackPasswordUtility)
        try:
            password_manager.validate_credentials_for_enrollment(self.context,
                                                                 username,
                                                                 password)
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
        unused_enrollment_ds_intid, scorm_id = parse_registration_id(report.registration_id)
        registration_id = get_registration_id_for_user_and_course(scorm_id,
                                                                  user,
                                                                  course)
        if registration_id != report.registration_id:
            logger.info(u"Postback regid (%s) does not match enrollment regid (%s)",
                        report.registration_id, registration_id)
            return hexc.HTTPBadRequest()
        container = IRegistrationReportContainer(course)
        user_container = container.get(user.username)
        if not user_container:
            user_container = UserRegistrationReportContainer()
            container[user.username] = user_container

        self.process(scorm_id, user, course, user_container, report)
        logger.info(u"Registration report postback stored (user=%s) (scorm_id=%s)",
                    user.username,
                    scorm_id)
        return hexc.HTTPNoContent()

