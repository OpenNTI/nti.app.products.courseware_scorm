#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.schema.field import DecodingValidTextLine as ValidTextLine


class ISCORMCourseInstance(ICourseInstance):
    """
    A concrete instance of a SCORM course.
    """


class ISCORMCourseMetadata(interface.Interface):
    """
    Metadata for a SCORM course.
    """

    scorm_id = ValidTextLine(title=u"The SCORM ID",
                             required=True)
