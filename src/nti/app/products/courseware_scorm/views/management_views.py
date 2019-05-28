#!/usr/bin/env python
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
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.courseware_admin.views.management_views import CreateCourseView

from nti.app.products.courseware_scorm import SCORM_COLLECTION_NAME

from nti.app.products.courseware_scorm import MessageFactory as _

from nti.app.products.courseware_scorm.courses import is_course_admin
from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.interfaces import ISCORMCollection
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.app.products.courseware_scorm.views import UPDATE_SCORM_VIEW_NAME
from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import IMPORT_SCORM_COURSE_VIEW_NAME

from nti.common.string import is_true

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseAdministrativeLevel

from nti.dataserver.authorization import ACT_CONTENT_EDIT

from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.proxy import removeAllProxies

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

    def upload_content(self, source, tags=None):
        """
        Upload the content to scorm cloud, optionally tagging it as requested.

        Returns the newly created scorm content scorm_id.
        """
        client = component.getUtility(ISCORMCloudClient)
        try:
            scorm_id = client.import_scorm_content(source,
                                                   request=self.request)
            if tags:
                client.set_scorm_tags(scorm_id, tags)
        except ScormCloudError as exc:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': exc.message,
                             },
                             None)
        return scorm_id
@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='POST',
             name=IMPORT_SCORM_COURSE_VIEW_NAME)
class ImportSCORMCourseView(AbstractAdminScormCourseView,
                            SCORMContentUploadMixin):
    """
    A view for importing uploaded SCORM courses to SCORM Cloud.
    """

    def _do_call(self):
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
        entry_ntiid = ICourseCatalogEntry(self.context).ntiid
        scorm_id = self.upload_content(source, tags=(entry_ntiid,))
        metadata = ISCORMCourseMetadata(self.context)
        if metadata.has_scorm_package() and self.unregister_users:
            # Unregister users. We'll rely on launching to re-register users as
            # needed.
            client = component.getUtility(ISCORMCloudClient)
            try:
                client.unregister_users_for_scorm_content(source)
            except ScormCloudError as exc:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': exc.message,
                                 },
                                 None)
        course = removeAllProxies(self.context)
        interface.alsoProvides(course, ISCORMCourseInstance)
        metadata.scorm_id = scorm_id
        return self.context

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


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='POST',
             name=UPDATE_SCORM_VIEW_NAME)
class UpdateSCORMView(AbstractAdminScormCourseView):

    def _do_call(self):
        sources = get_all_sources(self.request)
        if sources:
            source = self._handle_multipart(sources)
        if not source:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"No SCORM zip file was included with request."),
                             },
                             None)
        client = component.getUtility(ISCORMCloudClient)
        metadata = ISCORMCourseMetadata(self.context)
        try:
            client.update_assets(metadata.scorm_id, source, self.request)
        except ScormCloudError as exc:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': exc.message,
                             },
                             None)

        return self.context

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


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMCollection,
             request_method='GET')
class SCORMCollectionView(AbstractAuthenticatedView):
    """
    A view for fetching :class:`ISCORMInstance` objects. This is open only
    to global editors and admins.
    """

    def _get_client(self):
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

    def _get_parent_site_name(self):
        site_admin_manager = component.getUtility(ISiteAdminManagerUtility)
        result = site_admin_manager.get_parent_site_name()
        if result and result != 'dataserver2':
            return result

    @Lazy
    def site_filter_tag_strs(self):
        result = (getSite().__name__,)
        parent_name = self._get_parent_site_name()
        if parent_name:
            result = (getSite().__name__, parent_name)
        return result

    def _include_filter(self, scorm_content):
        return set(self.site_filter_tag_strs) & set(scorm_content.tags or ())

    def _get_scorm_instances(self, client):
        if not is_admin_or_content_admin_or_site_admin(self.remoteUser):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'code': u'SCORMForbiddenError'
                             },
                             None)
        return client.get_scorm_instances()

    def __call__(self):
        client = self._get_client()
        items = self.get_scorm_instances(client)
        filtered_items = [x for x in items if self._include_filter(x)]
        result = LocatedExternalDict()
        result[ITEMS] = filtered_items
        result[ITEM_COUNT] = len(filtered_items)
        result[TOTAL] = len(items)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ISCORMCollection,
             request_method='PUT')
class SCORMCollectionPutView(AbstractAuthenticatedView):
    """
    A view for fetching :class:`ISCORMInstance` objects. This is open only
    to global editors and admins.
    """

    def _get_client(self):
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

    @Lazy
    def filter_tag_str(self):
        return getSite().__name__

    def _include_filter(self, scorm_content):
        return self.filter_tag_str in scorm_content.tags

    def _get_scorm_instances(self, client):
        if not is_admin_or_content_admin_or_site_admin(self.remoteUser):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'code': u'SCORMForbiddenError'
                             },
                             None)
        return client.get_scorm_instances()

    def __call__(self):
        client = self._get_client()
        items = self.get_scorm_instances(client)
        filtered_items = [x for x in items if self._include_filter(x)]
        result = LocatedExternalDict()
        result[ITEMS] = filtered_items
        result[ITEM_COUNT] = len(filtered_items)
        result[TOTAL] = len(items)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=ACT_CONTENT_EDIT,
             name=SCORM_COLLECTION_NAME)
class SCORMCourseCollectionView(SCORMCollectionView):
    """
    A view for fetching :class:`ISCORMInstance` objects tied to
    this particular course.
    """

    @Lazy
    def course_filter_tag_str(self):
        return ICourseCatalogEntry(self.context).ntiid

    def _include_filter(self, scorm_content):
        return self.course_filter_tag_str in scorm_content.tags \
            or super(SCORMCourseCollectionView, self)._include_filter(scorm_content)
