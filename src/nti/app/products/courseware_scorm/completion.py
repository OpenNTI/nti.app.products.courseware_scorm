#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from zope import component
from zope import interface

from nti.app.products.courseware_scorm.interfaces import ISCORMProgress
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.contenttypes.completion.interfaces import ICompletableItemCompletionPolicy
from nti.contenttypes.completion.interfaces import IRequiredCompletableItemProvider

from nti.contenttypes.completion.completion import CompletedItem

from nti.contenttypes.completion.interfaces import IUserProgressUpdatedEvent

from nti.contenttypes.completion.policies import AbstractCompletableItemCompletionPolicy

from nti.contenttypes.completion.progress import Progress

from nti.contenttypes.completion.utils import update_completion

from nti.coremetadata.interfaces import IUser

from nti.externalization.persistence import NoPickle


@interface.implementer(ISCORMProgress)
class SCORMProgress(Progress):

    def __init__(self, user, metadata, course, report):
        self.NTIID = metadata.ntiid
        self.Item = metadata
        self.CompletionContext = course
        self.registration_report = report

        super(SCORMProgress, self).__init__(User=user, LastModified=datetime.utcnow())

    @property
    def AbsoluteProgress(self):
        report = self.registration_report
        activity = report.activity
        if activity is not None:
            progress = 1 if (activity.complete or activity.completed) else 0
        else:
            progress = 1 if report.complete else 0
        return progress

    @property
    def HasProgress(self):
        return self.registration_report.total_time > 0

    @property
    def MaxPossibleProgress(self):
        return 1


@component.adapter(IUser, ISCORMCourseMetadata, ISCORMCourseInstance)
def _scorm_progress(user, metadata, course):
    report_container = IUserRegistrationReportContainer(metadata)
    report = report_container.get_registration_report(user)
    if report is None:
        return None
    return SCORMProgress(user,
                         metadata,
                         course,
                         report)


@component.adapter(ISCORMCourseInstance)
@interface.implementer(IRequiredCompletableItemProvider)
class _SCORMCompletableItemProvider(object):

    def __init__(self, course):
        self.course = course

    def iter_items(self, unused_user):
        items = []
        metadata = ISCORMCourseMetadata(self.course)
        if metadata.has_scorm_package():
            items.append(metadata)
        return items


@NoPickle
@component.adapter(ISCORMCourseMetadata, ISCORMCourseInstance)
@interface.implementer(ICompletableItemCompletionPolicy)
class SCORMCompletionPolicy(AbstractCompletableItemCompletionPolicy):

    def __init__(self, metadata, course):
        self.metadata = metadata
        self.course = course

    def is_complete(self, progress):
        result = None

        if progress is None:
            return result

        if not ISCORMProgress.providedBy(progress):
            return result

        report = progress.registration_report
        if report is None:
            return result

        activity = report.activity
        if activity is not None:
            completed = activity.complete or activity.completed
        else:
            completed = report.complete

        if completed:
            result = CompletedItem(Item=progress.Item,
                                   Principal=progress.User,
                                   CompletedDate=progress.LastModified)
        return result


@component.adapter(ISCORMCourseMetadata, IUserProgressUpdatedEvent)
def _on_user_progress_updated(metadata, event):
    user = event.user
    course = event.context
    update_completion(metadata, metadata.ntiid, user, course)
