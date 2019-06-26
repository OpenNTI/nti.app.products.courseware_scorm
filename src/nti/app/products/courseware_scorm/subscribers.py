#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zc.intid.interfaces import IBeforeIdRemovedEvent

from zope import component
from zope import interface

from nti.app.contenttypes.presentation.utils.asset import remove_presentation_asset
from nti.app.products.courseware.interfaces import IAllCoursesCollection
from nti.app.products.courseware.interfaces import IAllCoursesCollectionAcceptsProvider

from nti.app.products.courseware_scorm.courses import SCORM_COURSE_MIME_TYPE

from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo

from nti.contentlibrary.indexed_data import get_site_registry
from nti.contentlibrary.indexed_data import get_library_catalog

from nti.site.site import get_component_hierarchy_names

logger = __import__('logging').getLogger(__name__)


# Disabled: jz - 6.2019
@component.adapter(IAllCoursesCollection)
@interface.implementer(IAllCoursesCollectionAcceptsProvider)
class SCORMAllCoursesCollectionAcceptsProvider(object):

    def __init__(self, courses_collection):
        self.courses_collection = courses_collection

    def __iter__(self):
        if component.queryUtility(ISCORMCloudClient) is not None:
            return iter([SCORM_COURSE_MIME_TYPE])
        return iter(())


@component.adapter(ISCORMContentInfo, IBeforeIdRemovedEvent)
def _on_scorm_content_removed(scorm_content, unused_event):
    """
    Remove scorm content refs pointed to deleted content.
    """
    count = 0
    content_ntiid = getattr(scorm_content, 'ntiid', None)
    registry = get_site_registry()
    if not content_ntiid:
        return count

    catalog = get_library_catalog()
    sites = get_component_hierarchy_names()
    items = catalog.search_objects(provided=ISCORMContentRef,
                                   target=content_ntiid,
                                   sites=sites)
    for item in items or ():
        if      ISCORMContentRef.providedBy(item) \
            and content_ntiid == getattr(item, 'target', ''):
            # This ends up removing from containers.
            remove_presentation_asset(item, registry)
            count += 1
    if count:
        logger.info('Removed scorm_content (%s) from %s overview group(s)',
                    content_ntiid, count)
    return count
