#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of an Atom/OData workspace and collection for scorm content.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IRequest

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.container.contained import Contained

from zope.location.interfaces import IContained

from zope.traversing.interfaces import IPathAdapter

from nti.appserver.workspaces.interfaces import IUserService

from nti.app.products.courseware_scorm import SCORM_WORKSPACE
from nti.app.products.courseware_scorm import SCORM_COLLECTION_NAME

from nti.app.products.courseware_scorm.interfaces import ISCORMWorkspace
from nti.app.products.courseware_scorm.interfaces import ISCORMCollection
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.dataserver.authorization import is_admin_or_content_admin_or_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.property.property import alias

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISCORMCollection)
class SCORMInstanceCollection(Contained):
    """
    A collection containing all scorm instances (fetched from scorm cloud).
    This also acts as a proxy for uploading new scorm content to scorm cloud.
    """

    __name__ = SCORM_COLLECTION_NAME

    accepts = ()
    links = ()

    name = alias('__name__', __name__)

    def __init__(self, container):
        self.__parent__ = container

    def _get_parent_site_name(self):
        site_admin_manager = component.getUtility(ISiteAdminManagerUtility)
        result = site_admin_manager.get_parent_site_name()
        if result and result != 'dataserver2':
            return result

    @Lazy
    def tags(self):
        result = (getSite().__name__,)
        parent_name = self._get_parent_site_name()
        if parent_name:
            result = (getSite().__name__, parent_name)
        return result

    def _include_filter(self, scorm_content):
        return set(self.tags) & set(scorm_content.tags or ())

    @Lazy
    def scorm_instances(self):
        """
        Return available scorm instances.
        """
        scorm_utility = component.queryUtility(ISCORMCloudClient)
        result = ()
        if scorm_utility is not None:
            result = scorm_utility.get_scorm_instances()
            result = [x for x in result if self._include_filter(x)]
        return result

    @Lazy
    def container(self):
        return self.scorm_instances


@interface.implementer(ISCORMWorkspace, IContained)
class _SCORMWorkspace(object):

    __parent__ = None
    __name__ = SCORM_WORKSPACE

    name = alias('__name__')

    def __init__(self, user_service):
        self.context = user_service
        self.user = user_service.user

    @Lazy
    def collections(self):
        """
        The returned collections are sorted by name.
        """
        return (SCORMInstanceCollection(self),)

    @property
    def links(self):
        return ()

    def __getitem__(self, key):
        """
        Make us traversable to collections.
        """
        for i in self.collections:
            if i.__name__ == key:
                return i
        raise KeyError(key)

    def __len__(self):
        return len(self.collections)

    def predicate(self):
        scorm_utility = component.queryUtility(ISCORMCloudClient)
        return  scorm_utility is not None \
            and is_admin_or_content_admin_or_site_admin(self.user)


@interface.implementer(ISCORMWorkspace)
@component.adapter(IUserService)
def SCORMWorkspace(user_service):
    workspace = _SCORMWorkspace(user_service)
    if workspace.predicate():
        workspace.__parent__ = workspace.user
        return workspace


@interface.implementer(IPathAdapter)
@component.adapter(IUser, IRequest)
def SCORMPathAdapter(context, unused_request):
    service = IUserService(context)
    workspace = ISCORMWorkspace(service)
    return workspace


class CourseScormInstanceCollection(SCORMInstanceCollection):

    @Lazy
    def tags(self):
        return (ICourseCatalogEntry(self.context).ntiid,)

    def _include_filter(self, scorm_content):
        return set(self.tags) & set(scorm_content.tags or ()) \
            or super(CourseScormInstanceCollection, self)._include_filter(scorm_content)


def course_scorm_collection_path_adapter(course, unused_request):
    return CourseScormInstanceCollection(course)
