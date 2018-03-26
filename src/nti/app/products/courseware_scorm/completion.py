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

from nti.app.products.courseware_scorm.interfaces import ISCORMProgress
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata

from nti.contenttypes.completion.interfaces import ICompletedItemProvider
from nti.contenttypes.completion.interfaces import IRequiredCompletableItemProvider

from nti.contenttypes.completion.progress import Progress

from nti.coremetadata.interfaces import IUser


@interface.implementer(ISCORMProgress)
class SCORMProgress(Progress):
    
    def __init__(self, User, report):
        self.registration_report = report

        activity = report.activity
        runtime = activity.runtime if activity is not None else None
        if runtime is not None:
            progress = report.activity.runtime.progress_measure
        elif activity is not None:
            progress = 1 if report.activity.complete else 0
        else: 
            progress = 1 if report.complete else 0
        self.AbsoluteProgress = progress
            
        self.MaxPossibleProgress = 1
        self.HasProgress = report.total_time > 0
        
        super(SCORMProgress, self).__init__(User=User, LastModified=None)
        

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
