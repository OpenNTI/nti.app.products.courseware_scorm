#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from zope import interface

from nti.contenttypes.courses.interfaces import ICourseInstance


class IScormCourseInstance(ICourseInstance):
    """
    A concrete instance of a SCORM course.
    """
    pass
