#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecordCreatedEvent

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseInstance
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient


@component.adapter(ICourseInstanceEnrollmentRecord,
                   ICourseInstanceEnrollmentRecordCreatedEvent)
def _enrollment_record_created(record, event):
    if not ISCORMCourseInstance.providedBy(record.CourseInstance):
        return
    client = component.getUtility(ISCORMCloudClient)
    client.sync_enrollment_record(record)
