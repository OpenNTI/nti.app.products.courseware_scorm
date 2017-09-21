#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from nti.app.products.courseware_admin.views.management_views import CreateCourseView

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

class CreateSCORMCourseView(CreateCourseView):
    """
    An object that can create SCORM courses.
    """

    _COURSE_INSTANCE_FACTORY = SCORMCourseInstance
