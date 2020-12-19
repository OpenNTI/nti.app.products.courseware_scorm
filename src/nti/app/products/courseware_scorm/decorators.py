#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.products.courseware_scorm import SCORM_COLLECTION_NAME

from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfoContainer

from nti.app.products.courseware_scorm.views import SCORM_PROGRESS_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import PREVIEW_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import SCORM_CONTENT_ASYNC_UPLOAD_UPDATE_VIEW

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.contenttypes.completion.interfaces import ICompletionContextCompletedItem
from nti.contenttypes.completion.interfaces import IPrincipalCompletedItemContainer

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import is_course_instructor_or_editor

from nti.dataserver.authorization import ACT_CONTENT_EDIT

from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.traversal.traversal import find_interface

LINKS = StandardExternalFields.LINKS
ITEMS = StandardExternalFields.ITEMS
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

LAUNCH_REL = LAUNCH_SCORM_COURSE_VIEW_NAME
PROGRESS_REL = SCORM_PROGRESS_VIEW_NAME


@component.adapter(ISCORMContentRef)
@interface.implementer(IExternalObjectDecorator)
class _SCORMContentRefDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, external):
        external['ScormContentInfo'] = find_object_with_ntiid(context.target)
        external['Target-NTIID'] = context.target


@component.adapter(ISCORMContentInfo)
@interface.implementer(IExternalObjectDecorator)
class _SCORMContentInfoLaunchDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_external):
        return context.upload_job is None \
            or context.upload_job.is_upload_successfully_complete()

    def _do_decorate_external(self, context, external):
        course = find_interface(context, ICourseInstance, strict=False)
        if course is not None:
            _links = external.setdefault(LINKS, [])
            if    is_admin_or_content_admin_or_site_admin(self.remoteUser) \
               or is_course_instructor_or_editor(course, self.remoteUser):
                _links.append(Link(context,
                                   rel=LAUNCH_REL,
                                   elements=(PREVIEW_SCORM_COURSE_VIEW_NAME,)))
            else:
                _links.append(Link(context,
                                   rel=LAUNCH_REL,
                                   elements=(LAUNCH_SCORM_COURSE_VIEW_NAME,)))
                _links.append(Link(context,
                                   rel=PROGRESS_REL,
                                   elements=(PROGRESS_REL,)))


@component.adapter(ISCORMContentInfo)
@interface.implementer(IExternalObjectDecorator)
class _SCORMContentInfoDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorate the scorm content info.
    """

    def _predicate(self, context, unused_external):
        return has_permission(ACT_CONTENT_EDIT, context, self.request)

    def _do_decorate_external(self, context, external):
        _links = external.setdefault(LINKS, [])
        _links.append(Link(context, rel='delete'))
        if context.upload_job and not context.upload_job.is_upload_complete():
            _links.append(Link(context,
                               rel=SCORM_CONTENT_ASYNC_UPLOAD_UPDATE_VIEW))


@component.adapter(ICourseInstance)
@interface.implementer(IExternalObjectDecorator)
class _CourseInstanceDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorate scorm collection rel for this course instance.
    """

    def _predicate(self, context, unused_external):
        return  component.queryUtility(ISCORMCloudClient) is not None \
            and has_permission(ACT_CONTENT_EDIT, context, self.request)

    def _do_decorate_external(self, context, external):
        _links = external.setdefault(LINKS, [])
        _links.append(
            Link(context,
                 rel=SCORM_COLLECTION_NAME,
                 elements=(SCORM_COLLECTION_NAME,))
        )


@component.adapter(ICompletionContextCompletedItem)
@interface.implementer(IExternalMappingDecorator)
class CourseCompletedItemDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    For a course completed item, return the scorm metadata, including
    scorm pass/fail info.
    """

    def _predicate(self, unused_context, unused_result):
        return bool(self._is_authenticated)

    def build_completion_meta(self, scorm_content, completed_item):
        result = {}
        result['MimeType'] = 'application/vnd.nextthought.scormcompletionmetadata'
        result['ScormContentInfoTitle'] = scorm_content.title
        result['ScormContentInfoNTIID'] = scorm_content.ntiid
        result['CompletionDate'] = completed_item.CompletedDate
        result['Success'] = completed_item.Success
        return result

    def _do_decorate_external(self, context, result):
        progress = context.__parent__
        course = progress.CompletionContext
        if not ICourseInstance.providedBy(course):
            return
        user = context.user
        meta_data = result.setdefault('CompletionMetadata', {})
        meta_items = meta_data.setdefault(ITEMS, [])
        principal_container = component.queryMultiAdapter((user, course),
                                                          IPrincipalCompletedItemContainer)
        success_count = result.setdefault('SuccessCount', 0)
        fail_count = result.setdefault('FailCount', 0)
        for scorm_content in ISCORMContentInfoContainer(course).values():
            completed_item = principal_container.get_completed_item(scorm_content)
            if completed_item is not None:
                completion_meta = self.build_completion_meta(scorm_content,
                                                             completed_item)
                if completion_meta['Success']:
                    success_count += 1
                else:
                    fail_count += 1
                meta_items.append(completion_meta)
        meta_data[ITEM_COUNT] = len(meta_items)
        meta_data['SuccessCount'] = success_count
        meta_data['FailCount'] = fail_count
