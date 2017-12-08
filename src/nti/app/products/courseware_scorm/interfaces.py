#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

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

    def import_course(path):
        """
        Imports an uploaded SCORM course from the given path.
        :param path: The path which locates the SCORM course to import.
        """

    def upload_course(self, source, redirect_url):
        """
        Uploads a SCORM zip to the SCORM Cloud server.

        :param source The SCORM course zip file to upload to SCORM Cloud.
        :param redirect_url The URL to which the client will be redirected after
            the upload completes.
        """


class IScormIdentifier(interface.Interface):
    """
    Provides SCORM identifiers for importing courses.
    """

    def get_id(self):
        """
        Returns the SCORM identifier of the adapted course.
        """

    def get_object(self):
        """
        Returns the adapted course.
        """
