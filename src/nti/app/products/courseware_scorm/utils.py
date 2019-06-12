#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef

from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contenttypes.courses.common import get_course_packages

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.courses.utils import get_parent_course

from nti.site.site import get_component_hierarchy_names

logger = __import__('logging').getLogger(__name__)


def get_registration_id_for_user_and_course(scorm_id, user, course):
    """
    The user's enrollment record ds_intid and the scorm id, separated
    by an underscore.
    """
    identifier = component.getMultiAdapter((user, course),
                                            ISCORMIdentifier)
    return '%s_%s' % (identifier.get_id(), scorm_id)


def parse_registration_id(registration_id):
    """
    Split the registration_id into the user's enrollment record ds_intid and
    the scorm id.
    """
    return registration_id.split('_')


def _pkg_containers(package):
    result = []
    def recur(unit):
        for child in unit.children or ():
            recur(child)
        result.append(unit.ntiid)
    recur(package)
    return result


def _course_containers(course):
    result = set()
    courses = {course, get_parent_course(course)}
    courses.discard(None)
    for _course in courses:
        entry = ICourseCatalogEntry(_course)
        for package in get_course_packages(_course):
            result.update(_pkg_containers(package))
        result.add(entry.ntiid)
    return result


def get_scorm_refs(course, scorm_id):
    """
    Return all scorm content refs in lessons in our course, returning
    the collection that matches the given scorm_id.
    """
    catalog = get_library_catalog()
    intids = component.getUtility(IIntIds)
    container_ntiids = _course_containers(course)
    result = []
    for item in catalog.search_objects(intids=intids,
                                       container_all_of=False,
                                       container_ntiids=container_ntiids,
                                       sites=get_component_hierarchy_names(),
                                       provided=(ISCORMContentRef,)):
        if item.scorm_id == scorm_id:
            result.append(item)
    return result
