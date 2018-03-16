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

from nti.contenttypes.courses.interfaces import INonExportable
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import ListOrTuple
from nti.schema.field import DecodingValidTextLine as ValidTextLine


class ISCORMCourseInstance(ICourseInstance, INonExportable):
    """
    A concrete instance of a SCORM course.
    """


class ISCORMCourseMetadata(IContained):
    """
    Metadata for a SCORM course.
    """

    scorm_id = ValidTextLine(title=u"The SCORM ID",
                             required=False)

    def has_scorm_package():
        """
        Whether a SCORM package has been uploaded to the course.
        """


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

    def update_assets(course, source):
        """
        Updates the existing SCORM package with assets from a new package.

        :param course: The course whose package should be updated.
        :param source: The new package used to update the existing package.
        """

    def delete_course(course):
        """
        Deletes the SCORM package associated with the given ISCORMCourseInstance.

        :param course: The course for which to delete the associated SCORM package.
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

    def get_registration_list(course):
        """
        Returns the list of registrations for the given course.
        """

    def delete_all_registrations(course):
        """
        Deletes all SCORM Cloud registrations for the specified course.
        """

    def get_registration_progress(enrollment_record):
        """
        Returns progress for the registration of the specified user and course.
        """
        
    def enrollment_registration_exists(enrollment_record):
        """
        Returns whether a registration exists for the given enrollment record.
        """

    def registration_exists(registration_id):
        """
        Returns whether a registration with the given ID exists.
        """
        
    def get_archive(course):
        """
        Returns the SCORM archive for the specified course.
        """

    def get_metadata(course):
        """
        Returns the SCORM metadata associated with the specified course.
        """


class ISCORMIdentifier(interface.Interface):
    """
    Provides SCORM identifiers for importing courses.
    """

    def get_id():
        """
        Returns the SCORM identifier of the adapted course.
        """


class IScormInstance(interface.Interface):
    """
    A registration instance in a SCORM course.
    """

    instance_id = ValidTextLine(title=u'The ID of the instance.',
                                required=True)

    course_version = ValidTextLine(title=u'The course version.')

    update_date = ValidTextLine(title=u'The update date.')


class IScormRegistration(interface.Interface):
    """
    A learner registration in a SCORM course.
    """

    app_id = ValidTextLine(title=u'The app ID.',
                           required=True)

    course_id = ValidTextLine(title=u'The course ID.',
                              required=True)

    registration_id = ValidTextLine(title=u'The registration ID.',
                                    required=True)

    completed_date = ValidTextLine(title=u'The date the registration was completed.')

    course_title = ValidTextLine(title=u'The course title.')

    create_date = ValidTextLine(title=u'The date the registration was created.')

    email = ValidTextLine(title=u'The registered email.')

    first_access_date = ValidTextLine(title=u'The date the registration was first accessed.')

    instances = ListOrTuple(title=u'The registration instances.')

    last_access_date = ValidTextLine(title=u'The date the registration was last accessed.')

    last_course_version_launched = ValidTextLine(title=u'The last version of the course '
                                                 u'that was launched by this registration.')

    learner_id = ValidTextLine(title=u'The ID of the registered learner.')

    learner_first_name = ValidTextLine(title=u'The first name of the registered learner.')

    learner_last_name = ValidTextLine(title=u'The last name of the registered learner.')


class ISCORMProgress(interface.Interface):
    """
    An object containing high-level information about a registration result.
    """

    complete = Bool(title=u'Whether the registration has been completed.')

    success = Bool(title=u'Whether the registration has been passed or failed.')

    score = Number(title=u'The score, from 0 to 100.')

    total_time = Number(title=u'The total time tracked by the content player in seconds; \
                                that is, how long the learner had the course open.')
