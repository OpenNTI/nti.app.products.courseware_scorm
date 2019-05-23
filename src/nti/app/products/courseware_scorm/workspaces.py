#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of an Atom/OData workspace and collection for courses.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient
from nti.app.products.courseware_scorm.interfaces import IGlobalSCORMCollection

from nti.property.property import alias

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IGlobalSCORMCollection)
class SCORMInstanceCollection(Contained):
    """
    A report collection that will return all reports configured on the
    """

    __name__ = u'SCORMInstances'

    accepts = ()
    links = ()

    name = alias('__name__', __name__)

    def __init__(self, container):
        self.__parent__ = container.__parent__

    @Lazy
    def scorm_instances(self):
        """
        Return available scorm instances.
        """
        scorm_utility = component.queryUtility(ISCORMCloudClient)
        scorm_instances = scorm_utility.get_scorm_instances()
        return scorm_instances

    @Lazy
    def container(self):
        return self.scorm_instances


@interface.implementer(IGlobalSCORMCollection)
def scorm_instance_collection(workspace):
    scorm_utility = component.queryUtility(ISCORMCloudClient)
    if scorm_utility is not None:
        return SCORMInstanceCollection(workspace)
