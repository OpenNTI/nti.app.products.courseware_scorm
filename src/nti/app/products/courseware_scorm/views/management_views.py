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

from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME

from nti.common.string import is_true

from nti.contenttypes.courses.interfaces import ICourseAdministrativeLevel

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_CONTENT_EDIT

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

    def get_scorm_content(self, client, scorm_id):
        """
        Return the scorm content info referenced by the given scorm_id.
        """
        try:
            result = client.get_scorm_instance_detail(scorm_id)
        except ScormCloudError as exc:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': exc.message,
                             },
                             None)
        return result

    def _set_content_tags(self, client, scorm_id, tags):
        client.set_scorm_tags(scorm_id, tags)

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

    def copy_scorm_content_info(self, source, target):
        for name in ISCORMContentInfo.names():
            value = getattr(source, name, None)
            if value is not None:
                setattr(target, name, value)

    def update_upload_job(self, upload_job, async_result):
        upload_job.ErrorMessage = async_result.error_message
        upload_job.State = async_result.status

    def _get_async_import_result(self, client, token):
        return client.get_async_import_result(token)

    def __call__(self):
        client = self._get_scorm_client()
        upload_job = self.context.upload_job
        if upload_job and not upload_job.is_upload_complete():
            # Fetch job status
            async_result = self._get_async_import_result(client, upload_job.token)
            if async_result.status != upload_job.State:
                # State has changed, we need to update and commit.
                self.update_upload_job(upload_job, async_result)
                self.request.environ['nti.request_had_transaction_side_effects'] = True
                if upload_job.is_upload_successfully_complete():
                    new_content_info = self.get_scorm_content(client,
                                                              self.context.scorm_id)
                    # Collection has tag info
                    self._set_content_tags(client,
                                           self.context.scorm_id,
                                           self.context.__parent__.tags)
                    # Copy our non-null attributes from scorm cloud info
                    # into our context.
                    self.copy_scorm_content_info(new_content_info, self.context)
        return self.context


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
