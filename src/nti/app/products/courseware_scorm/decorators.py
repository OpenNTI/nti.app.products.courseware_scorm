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

from nti.app.products.courseware.utils import PreviewCourseAccessPredicateDecorator

from nti.app.products.courseware_scorm.courses import is_course_admin

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.app.products.courseware_scorm.views import UPDATE_SCORM_VIEW_NAME
from nti.app.products.courseware_scorm.views import GET_SCORM_ARCHIVE_VIEW_NAME
from nti.app.products.courseware_scorm.views import IMPORT_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import PREVIEW_SCORM_COURSE_VIEW_NAME

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import is_course_instructor_or_editor

from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from nti.links.links import Link

from nti.traversal.traversal import find_interface

LINKS = StandardExternalFields.LINKS

ARCHIVE_REL = GET_SCORM_ARCHIVE_VIEW_NAME
IMPORT_REL = IMPORT_SCORM_COURSE_VIEW_NAME
LAUNCH_REL = LAUNCH_SCORM_COURSE_VIEW_NAME

logger = __import__('logging').getLogger(__name__)


@component.adapter(ISCORMCourseInstance)
@interface.implementer(IExternalObjectDecorator)
class _SCORMCourseInstanceDecorator(AbstractAuthenticatedRequestAwareDecorator):

    # pylint: disable=arguments-differ
    def _do_decorate_external(self, original, external):
        # The Outline isn't needed; SCORM Cloud provides its own viewer
        external.pop('Outline', None)
        metadata = ISCORMCourseMetadata(original, None)
        external['Metadata'] = metadata
        if is_course_admin(self.remoteUser, original):
            _links = external.setdefault(LINKS, [])
            _links.append(
                Link(original, rel=IMPORT_REL, elements=(IMPORT_REL,))
            )
            # pylint: disable=too-many-function-args
            if metadata.has_scorm_package():
                for rel in (ARCHIVE_REL, UPDATE_SCORM_VIEW_NAME):
                    _links.append(Link(original,
                                       rel=rel,
                                       elements=(rel,)))


@component.adapter(ISCORMCourseMetadata)
@interface.implementer(IExternalObjectDecorator)
class _SCORMCourseInstanceMetadataDecorator(PreviewCourseAccessPredicateDecorator):

    @property
    def course(self):
        # TODO: Adapter
        return find_interface(self.context, ICourseInstance, strict=True)

    # pylint: disable=arguments-differ
    def _do_decorate_external(self, original, external):
        if original.has_scorm_package():
            course = self.course
            _links = external.setdefault(LINKS, [])
            element = LAUNCH_SCORM_COURSE_VIEW_NAME
            if is_admin_or_content_admin_or_site_admin(self.remoteUser) \
               or is_course_instructor_or_editor(course, self.remoteUser):
                element = PREVIEW_SCORM_COURSE_VIEW_NAME
            
            _links.append(
                Link(course, rel=LAUNCH_REL, elements=(element,))
            )
