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

    def launch(course, user, redirect_url):
        """
        Launches the given registration by redirecting the client's browser to
        the main launch page for the course associated with the registration.
        :param course The course instance for which to launch SCORM Cloud.
        :param user The user for whom to launch SCORM Cloud.
        :redirect_url: The URL upon which to redirect when the registration
                        has completed.
        """


class IScormIdentifier(interface.Interface):
    """
    Provides SCORM identifiers for importing courses.
    """

    def get_id():
        """
        Returns the SCORM identifier of the adapted course.
        """
