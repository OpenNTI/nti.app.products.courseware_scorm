#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import interface

from zope.location.interfaces import IContained

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.schema.field import DecodingValidTextLine as ValidTextLine


class ISCORMCourseInstance(ICourseInstance):
    """
    A concrete instance of a SCORM course.
    """


class ISCORMCourseMetadata(IContained):
    """
    Metadata for a SCORM course.
    """

    scorm_id = ValidTextLine(title=u"The SCORM ID",
                             required=True)


class ISCORMCloudClient(interface.Interface):
    """
    A client for interacting with SCORM Cloud.
    """

    def import_course(context, source):
        """
        Imports into SCORM Cloud a SCORM course from a zip file source.
        :param context: The course context under which to import the SCORM course.
        :param source: The SCORM course zip file source.
        """

    def upload_course(source, redirect_url):
        """
        Uploads a SCORM course zip file to the SCORM Cloud server.

        :param source The SCORM course zip file to upload to SCORM Cloud.
        :param redirect_url The URL to which the client will be redirected after
            the upload completes.
        """

    def sync_enrollment_record(enrollment_record, course):
        """
        Syncs a course enrollment record with SCORM Cloud.
        """

    def delete_enrollment_record(enrollment_record):
        """
        Removes a course enrollment registration from SCORM Cloud.
        """


class IScormIdentifier(interface.Interface):
    """
    Provides SCORM identifiers for importing courses.
    """

    def get_id():
        """
        Returns the SCORM identifier of the adapted course.
        """
