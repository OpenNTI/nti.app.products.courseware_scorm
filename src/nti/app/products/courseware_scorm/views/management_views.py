#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.view import view_config

from nti.dataserver import authorization as nauth

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.contenttypes.courses.interfaces import ICourseAdministrativeLevel

from nti.app.products.courseware_admin.views.management_views import CreateCourseView
from nti.app.products.courseware_admin.views.management_views import DeleteCourseView

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseAdministrativeLevel,
             request_method='POST',
             permission=nauth.ACT_NTI_ADMIN,
             name=CREATE_SCORM_COURSE_VIEW_NAME)
class CreateSCORMCourseView(CreateCourseView):
    """
    An object that can create SCORM courses.
    """

    _COURSE_INSTANCE_FACTORY = SCORMCourseInstance


class DeleteSCORMCourseView(DeleteCourseView):
    """
    A view for deleting SCORM courses.
    """


class UploadSCORMView(AbstractAuthenticatedView,
                      ModeledContentUploadRequestUtilsMixin):
    """
    A view for uploading SCORM zip archives to SCORM courses.
    """
