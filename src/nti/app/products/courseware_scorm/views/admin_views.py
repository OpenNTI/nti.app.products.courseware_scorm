#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import component

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.views import DELETE_ALL_REGISTRATIONS_VIEW_NAME
from nti.app.products.courseware_scorm.views import GET_REGISTRATION_LIST_VIEW_NAME

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver import authorization as nauth


@view_config(route_name='objects.generic.traversal',
renderer='rest',
context=ICourseInstance,
request_method='GET',
permission=nauth.ACT_NTI_ADMIN,
name=DELETE_ALL_REGISTRATIONS_VIEW_NAME)
class DeleteAllRegistrationsView(AbstractAuthenticatedView):
    """
    A view which allows admins to delete all SCORM registrations.
    """

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        client.delete_all_registrations(self.context)
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICourseInstance,
             request_method='GET',
             permission=nauth.ACT_NTI_ADMIN,
             name=GET_REGISTRATION_LIST_VIEW_NAME)
class GetRegistrationListView(AbstractAuthenticatedView):
    """
    A view which returns the SCORM Cloud registration list.
    """

    def __call__(self):
        client = component.getUtility(ISCORMCloudClient)
        registration_list = client.get_registration_list(self.context)
        return {'Items': registration_list}
