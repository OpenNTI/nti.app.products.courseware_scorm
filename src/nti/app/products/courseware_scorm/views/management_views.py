# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from requests.structures import CaseInsensitiveDict

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import get_safe_source_filename
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.courseware_admin.views.management_views import CreateCourseView

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.courses import is_course_admin
from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCollection
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo

from nti.app.products.courseware_scorm.utils import upload_scorm_content_async
from nti.app.products.courseware_scorm.utils import check_and_update_scorm_content_info

from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME

from nti.common.string import is_true

from nti.contenttypes.courses.interfaces import ICourseAdministrativeLevel

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_CONTENT_EDIT
from nti.dataserver.authorization import ACT_NTI_ADMIN

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.scorm_cloud.client.mixins import get_source

from nti.scorm_cloud.client.request import ScormCloudError

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseAdministrativeLevel,
             request_method='POST',
             name=CREATE_SCORM_COURSE_VIEW_NAME)
class CreateSCORMCourseView(CreateCourseView):
    """
    An object that can create SCORM courses.
    """

    _COURSE_INSTANCE_FACTORY = SCORMCourseInstance


class AbstractAdminScormCourseView(AbstractAuthenticatedView,
                                   ModeledContentUploadRequestUtilsMixin):

    @Lazy
    def _params(self):
        if self.request.body:
            values = super(AbstractAdminScormCourseView, self).readInput()
        else:
            values = self.request.params
        result = CaseInsensitiveDict(values)
        return result

    @property
    def unregister_users(self):
        """
        Defines whether we should unregister users when updating scorm content.
        Defaults to True.
        """
        result = self._params.get('reset-registrations', False)
        return is_true(result)

    def _check_access(self):
        if not is_course_admin(self.remoteUser, self.context):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'message': _(u"Cannot administer scorm courses."),
                             },
                             None)

    def __call__(self):
        self._check_access()
        return self._do_call()


class SCORMContentUploadMixin(object):
    """
    A class that is responsible for uploading scorm content as
    well as optionally tagging the content.
    """

    def _get_scorm_client(self):
        client = component.queryUtility(ISCORMCloudClient)
        if client is None:
            raise_json_error(self.request,
                             hexc.HTTPNotFound,
                             {
                                 'message': u'SCORM client not registered.',
                                 'code': u'SCORMClientNotFoundError'
                             },
                             None)
        return client


    def upload_content(self, source):
        """
        Upload the content asynchronously to scorm cloud.

        Returns the newly created :class:`IScormContentInfo`.
        """
        client = self._get_scorm_client()
        try:
            result = upload_scorm_content_async(source, client)
        except ScormCloudError as exc:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': exc.message,
                             },
                             None)
        return result

    def _handle_multipart(self, sources):
        """
        Returns a file source from the sources sent in a multi-part request.
        """
        for key in sources:
            raw_source = sources.get(key)
            source = get_source(raw_source)
            if source:
                break
        return source

    def _get_scorm_source(self):
        sources = get_all_sources(self.request)
        source = None
        if sources:
            source = self._handle_multipart(sources)
        if not source:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"No SCORM zip file was included with request."),
                             },
                             None)
        # Scorm cloud has issues with certain filenames (filenames with spaces
        # seemed fine - maybe it has something to do with special characters &- and
        # spaces). We sanitize here before we upload. The error message from scorm
        # cloud is entirely useless - Internal Server Error
        source.filename = get_safe_source_filename(source, 'scorm_upload.zip')
        return source


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMCollection,
             permission=ACT_READ,
             request_method='GET')
class SCORMCollectionView(AbstractAuthenticatedView):
    """
    A view for fetching :class:`ISCORMInstance` objects. This is open only
    to global editors and admins.
    """

    def __call__(self):
        result = LocatedExternalDict()
        result[ITEMS] = items = self.context.scorm_instances
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMCollection,
             permission=ACT_CONTENT_EDIT,
             request_method='PUT')
class SCORMCollectionPutView(AbstractAuthenticatedView,
                             ModeledContentUploadRequestUtilsMixin,
                             SCORMContentUploadMixin):
    """
    A view for uploading a scorm package to our site-specific
    :class:`ISCORMCollection`.
    """

    def _do_call(self):
        source = self._get_scorm_source()
        scorm_content_info = self.upload_content(source)
        scorm_content_info.creator = self.remoteUser.username
        self.context.store_content(scorm_content_info)
        return scorm_content_info


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMContentInfo,
             permission=ACT_CONTENT_EDIT,
             request_method='GET')
class ScormContentInfoGetView(AbstractAuthenticatedView,
                              SCORMContentUploadMixin):
    """
    A view for getting a :class:`ISCORMContentInfo` object. If this content
    is incomplete due to an asynchronous upload, we attempt to check on the
    status of the upload, pulling down the scorm content info if the upload
    has completed.
    """


    def __call__(self):
        client = self._get_scorm_client()
        upload_job = self.context.upload_job
        if upload_job and not upload_job.is_upload_complete():
            # Fetch and update
            try:
                did_update = check_and_update_scorm_content_info(self.context, client)
            except ScormCloudError as exc:
                logger.exception("Scorm exception while getting result (%s) (%s) (%s)",
                                 upload_job.token, self.context.ntiid, self.context.scorm_id)
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                    'message': exc.message,
                                 },
                                 None)
            if did_update:
                self.request.environ['nti.request_had_transaction_side_effects'] = True
        return self.context

@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMContentInfo,
             permission=ACT_NTI_ADMIN, #NTI Admins for now, editors may make sense in the future
             request_method='GET',
             name="launch_property_editor")
class ScormContentInfoPropertiesEditor(AbstractAuthenticatedView,
                                       SCORMContentUploadMixin):
    """
    A view that redirects the request to the properties editor
    of the scorm package. Useful for advanced configuration options.
    """

    def __call__(self):
        client = self._get_scorm_client()
        course_id = self.context.scorm_id
        url = client.launch_property_editor_url(course_id)
        return hexc.HTTPSeeOther(location=url)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMContentInfo,
             permission=ACT_CONTENT_EDIT,
             request_method='DELETE')
class ScormContentInfoDeleteView(AbstractAuthenticatedView,
                                 SCORMContentUploadMixin):
    """
    A view for deleting a :class:`ISCORMContentInfo` object from scorm_cloud.
    """

    def _delete_scorm_course(self, scorm_id):
        client = self._get_scorm_client()
        try:
            client.delete_course(scorm_id)
        except ScormCloudError as exc:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': exc.message,
                             },
                             None)

    def __call__(self):
        self._delete_scorm_course(self.context.scorm_id)
        self.context.__parent__.remove_content(self.context.scorm_id)
        return hexc.HTTPNoContent()
