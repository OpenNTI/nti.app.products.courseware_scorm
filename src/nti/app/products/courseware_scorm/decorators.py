#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.singleton import Singleton

from nti.links.links import Link

from nti.traversal.traversal import find_interface

from zope import component
from zope import interface

CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
LINKS = StandardExternalFields.LINKS
MIMETYPE = StandardExternalFields.MIMETYPE

LAUNCH_REL = LAUNCH_SCORM_COURSE_VIEW_NAME


@component.adapter(ISCORMCourseInstance)
@interface.implementer(IExternalObjectDecorator)
class _SCORMCourseInstanceDecorator(Singleton):

    def decorateExternalObject(self, original, external):
        # The Outline isn't needed; SCORM Cloud provides its own viewer
        external.pop('Outline', None)
        metadata = ISCORMCourseMetadata(original, None)
        external['Metadata'] = metadata


@component.adapter(ISCORMCourseMetadata)
@interface.implementer(IExternalObjectDecorator)
class _SCORMCourseInstanceMetadataDecorator(Singleton):

    def decorateExternalObject(self, original, external):
        _links = external.setdefault(LINKS, [])
        course = find_interface(original, ICourseInstance, strict=True)
        _links.append(Link(course, rel=LAUNCH_REL, elements=(LAUNCH_REL,)))