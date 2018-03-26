#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.contenttypes.completion.interfaces import ICompletedItemProvider
from nti.contenttypes.completion.interfaces import IRequiredCompletableItemProvider

from nti.coremetadata.interfaces import IUser


@component.adapter(IUser, ISCORMCourseInstance)
@interface.implementer(IRequiredCompletableItemProvider)
class _SCORMCompletableItemProvider(object):
    
    def __init__(self, user, course):
        self.user = user
        self.course = course
        
    def iter_items(self):
        items = []
        metadata = ISCORMCourseMetadata(self.course)
        if metadata.has_scorm_package():
            items.append(metadata)
        return items
    

@component.adapter(IUser, ISCORMCourseInstance)
@interface.implementer(ICompletedItemProvider)
class _SCORMCompletedItemProvider(object):
    
    def __init__(self, user, course):
        self.user = user
        self.course = course
    
    def completed_items(self):
        items = []
        return items
