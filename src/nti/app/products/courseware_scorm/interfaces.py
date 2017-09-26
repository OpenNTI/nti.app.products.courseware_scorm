#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from zope import interface

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.schema.field import TextLine as ValidTextLine

from zope.annotation.interfaces import IAttributeAnnotatable


class ISCORMCourseInstance(ICourseInstance, IAttributeAnnotatable):
    """
    A concrete instance of a SCORM course.
    """


class ISCORMCourseMetadata(interface.Interface):
    """
    Metadata for a SCORM course.
    """

    scorm_id = ValidTextLine(title=u"The SCORM ID",
                             required=True)
