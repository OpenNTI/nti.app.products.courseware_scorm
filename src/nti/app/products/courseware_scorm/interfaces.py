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

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.constraints import contains

from zope.container.interfaces import IContainer

from zope.location.interfaces import IContained

from nti.contenttypes.presentation.interfaces import IAssetRef
from nti.contenttypes.presentation.interfaces import INTIIDIdentifiable
from nti.contenttypes.presentation.interfaces import IGroupOverViewable
from nti.contenttypes.presentation.interfaces import INonExportableAsset
from nti.contenttypes.presentation.interfaces import ICoursePresentationAsset

from nti.base.interfaces import ICreated
from nti.base.interfaces import ILastModified

from nti.contenttypes.completion.interfaces import IProgress
from nti.contenttypes.completion.interfaces import ICompletableItem

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import IDoNotCreateDefaultOutlineCourseInstance

from nti.coremetadata.interfaces import IUser
from nti.coremetadata.interfaces import IShouldHaveTraversablePath

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Choice
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import DateTime
from nti.schema.field import ListOrTuple
from nti.schema.field import IndexedIterable as TypedIterable
from nti.schema.field import DecodingValidTextLine as ValidTextLine


class ISCORMContent(ICreated, ILastModified, IContained, IAttributeAnnotatable, ICompletableItem):
    """
    A basic scorm content holder, pointing to scorm content.
    """

    scorm_id = ValidTextLine(title=u"The SCORM ID",
                             required=False)


class ISCORMContentContainer(IShouldHaveTraversablePath, ILastModified, IContainer):
    """
    A storage container for :class:`ISCORMContent`.
    """

    contains(ISCORMContent)

    def store_content(content):
        """
        Store the given :class:`IScormContent` into this container.
        """

    def remove_content(content):
        """
        Remove the given :class:`IScormContent`.
        """


class ISCORMCourseInstance(ICourseInstance, IDoNotCreateDefaultOutlineCourseInstance):
    """
    A concrete instance of a SCORM course, where the outline is only a
    :class:`IScormContent`.
    """


class ISCORMContentRef(IAssetRef, IGroupOverViewable, INTIIDIdentifiable,
                       ICoursePresentationAsset,
                       INonExportableAsset):
    """
    A presentation asset ref pointing towards scorm content.
    """

    target = ValidNTIID(title=u"Target NTIID", required=True)


class ISCORMCourseMetadata(ISCORMContent):
    """
    Metadata for a SCORM course.
    """

    def has_scorm_package():
        """
        Whether a SCORM package has been uploaded to the course.
        """


class IPostBackURLUtility(interface.Interface):

    def url_for_registration_postback(enrollment_record, request=None):
        """
        Returns a url that should be used for registration result postbacks
        """


class IPostBackPasswordUtility(interface.Interface):

    def credentials_for_enrollment(reg_id):
        """
        Returns a tuple of username, passworod credentials to be used for this
        enrollment.
        """

    def validate_credentials_for_enrollment(reg_id, username, password):
        """
        Returns true if the username and password is correct for the enrollment.
        """


class ISCORMCloudClient(interface.Interface):
    """
    A client for interacting with SCORM Cloud.
    """

    def import_course(context, source):
        """
        Imports into SCORM Cloud a SCORM course from a zip file source.
        :param context: The course cotext under which to import the SCORM course.
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

    def get_registration_progress(course, user, results_format=None):
        """
        Returns progress for the registration of the specified user and course.
        """

    def enrollment_registration_exists(course, user):
        """
        Returns whether a registration exists for the given course and user.
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


class ISCORMObjective(interface.Interface):
    """
    An object containing summary information about an activity objective.
    """

    id = ValidTextLine(title=u'A unique label for the objective.',
                       required=True)

    measure_status = Bool(title=u'The measure status.',
                          required=True)

    normalized_measure = Number(title=u'The normalized measure.',
                                required=True)

    progress_status = Bool(title=u'The progress status.',
                           required=True)

    satisfied_status = Bool(title=u'The satisfied status.',
                            required=True)

    score_scaled = Number(title=u'A number that reflects the performance of the learner for the objective.',
                          required=False)

    score_min = Number(title=u'The minimum value, for the objective, in the range for the raw score.',
                       required=False)

    score_raw = Number(title=u'A number that reflects the performance of the learner, for the objective, \
                               relative to the range bounded by the values of min and max.',
                       required=False)

    success_status = Bool(title=u'Indicates whether the learner has mastered the objective.',
                          required=False,
                          default=None)

    completion_status = Choice(title=u'Indicates whether the learner has completed the associated objective.',
                               values=('completed', 'incomplete', 'not attempted', 'unknown'),
                               default=None,
                               required=False)

    progress_measure = Number(title=u'A measure of the progress the learner has made \
                                      toward completing the objective (in 0...1).',
                              required=False)

    description = ValidTextLine(title=u'A brief informative description of the objective.',
                                required=False)


class ISCORMComment(interface.Interface):
    """
    An object representing a comment or annotation associated with a SCO.
    """

    value = ValidTextLine(title=u'The comment text.',
                          required=False)

    location = ValidTextLine(title=u'The point in the SCO to which the comment applies.',
                             required=False)

    date_time = DateTime(title=u'The point in time at which the comment was created or most recently changed.',
                         required=False)


class ISCORMResponse(interface.Interface):
    """
    An object representing data generated when a learner responds to an interaction.
    """

    id = ValidTextLine(title=u'The response ID.',
                       required=False)

    value = ValidTextLine(title=u'The response value.',
                          required=False)


class ISCORMInteraction(interface.Interface):
    """
    An object which represents the results of a question response.
    """

    id = ValidTextLine(title=u'A unique label for the interaction.',
                       required=True)

    result = Choice(title=u'A judgment of the correctness of the learner response.',
                    values=('correct', 'incorrect', 'unanticipated', 'neutral'),
                    default=None,
                    required=False)

    latency = Number(title=u'The time elapsed between the time the interaction was made \
                            available to the learner for response and the time of the first response.',
                            required=False)

    timestamp = Number(title=u'The point in time at which the interaction was first made available to the learner \
                               for learner interaction and response.',
                               required=False)

    weighting = Number(title=u'The weight given to the interaction relative to other interactions.',
                       required=False)

    objectives = TypedIterable(title=u'The objectives associated with the interaction.',
                               value_type=Object(ISCORMObjective),
                               required=True)

    description = ValidTextLine(title=u'A brief informative description of the interaction.',
                                required=False)

    learner_response = Object(ISCORMResponse,
                              title=u'The data generated when a learner responds to an interaction.',
                              required=False)

    correct_responses = TypedIterable(title=u'The correct response patterns for the interaction.',
                                      value_type=Object(ISCORMResponse),
                                      default=None,
                                      required=False)


class ISCORMLearnerPreference(interface.Interface):
    """
    An object which represents a learner's preferences in an SCO.
    """

    language = ValidTextLine(title=u'The learner’s preferred language for SCOs with multilingual capability.',
                             required=False)

    audio_level = Number(title=u'Specifies an intended change in perceived audio level.',
                         required=False)

    delivery_speed = Number(title=u'The learner’s preferred relative speed of content delivery.',
                            required=False)

    audio_captioning = Choice(title=u'Specifies whether captioning text corresponding to audio is displayed.',
                              values=('-1', '0', '1'),
                              default=None,
                              required=False)


class ISCORMStatic(interface.Interface):
    """
    An object which represents static information about a SCORM runtime.
    """

    learner_id = ValidTextLine(title=u'The learner ID.',
                               required=False)

    launch_data = ValidTextLine(title=u'The launch data.',
                                required=False)

    learner_name = ValidTextLine(title=u'The learner name.',
                                 required=False)

    max_time_allowed = Number(title=u'The amount of accumulated time the learner is allowed to use an SCO.',
                              required=False)

    time_limit_action = Choice(title=u'Indicates what the SCO should do when max_time_allowed is exceeded.',
                               values=('exit,message', 'continue,message', 'exit,no message', 'continue,no message'),
                               default=None,
                               required=False)

    completion_threshold = Number(title=u'Used to determine whether the SCO should be considered complete (in 0...1).',
                                  required=False)

    scaled_passing_score = Number(title=u'Scaled passing score required to master the SCO (in -1...1).',
                                  required=False)


class ISCORMRuntime(interface.Interface):
    """
    An object containing summary information about an SCO runtime.
    """

    mode = Choice(title=u'Identifies one of three possible modes in which the SCO may be presented to the learner.',
                  values=('browse', 'normal', 'review'),
                  default=None,
                  required=False)

    exit = Choice(title=u'Indicates how or why the learner left the SCO.',
                  values=('timeout', 'suspend', 'logout', 'normal'),
                  default=None,
                  required=False)

    entry = ValidTextLine(title=u'Asserts whether the learner has previously accessed the SCO.',
                          required=False)

    credit = Bool(title=u'Indicates whether the learner will be credited for performance in the SCO.',
                  required=False)

    static = Object(ISCORMStatic,
                    title=u'Static information about the SCO runtime.',
                    default=None,
                    required=False)

    location = ValidTextLine(title=u'The learner’s current location in the SCO.',
                             required=False)

    score_raw = Number(title=u'Number that reflects the performance of the learner, for the objective, \
                               relative to the range bounded by the values of min and max.',
                       required=False)

    objectives = TypedIterable(title=u'The objectives.',
                               value_type=Object(ISCORMObjective),
                               required=True)

    total_time = Number(title=u'The sum of all of the learner’s session times accumulated in the current learner attempt.',
                               required=False)

    time_tracked = Number(title=u'The amount of time that the learner has spent in the current learner session for this SCO.',
                                 required=False)

    interactions = TypedIterable(title=u'The interactions associated with the SCO.',
                                 value_type=Object(ISCORMInteraction),
                                 required=True)

    score_scaled = Number(title=u'Number that reflects the performance of the learner, from -1 to 1.',
                          required=False)

    suspend_data = ValidTextLine(title=u'Provides space to store and retrieve data between learner sessions.',
                                 required=False)

    success_status = Bool(title=u'Indicates whether the learner has mastered the SCO (in 0...1).',
                          default=None,
                          required=False)

    progress_measure = Number(title=u'A measure of the progress the learner has made toward completing the SCO (in 0...1).',
                              required=False)

    completion_status = Choice(title=u'Indicates whether the learner has completed the SCO.',
                               values=('completed', 'incomplete', 'not attempted', 'unknown'),
                               default=None,
                               required=False)

    learner_preference = Object(ISCORMLearnerPreference,
                                title=u'The learner\'s preferences.',
                                default=None,
                                required=False)

    comments_from_lms = TypedIterable(title=u'The comments from the LMS.',
                                      value_type=Object(ISCORMComment),
                                      required=True)

    comments_from_learner = TypedIterable(title=u'The comments from the learner.',
                                          value_type=Object(ISCORMComment),
                                          required=True)


class ISCORMActivity(interface.Interface):
    """
    An object containing summary information about a registration activity.
    """

    id = ValidTextLine(title=u'The activity ID.',
                       required=True)

    title = ValidTextLine(title=u'The activity title.',
                          required=True)

    complete = Bool(title=u'Whether the activity has been completed.',
                    required=False,
                    default=None)

    success = Bool(title=u'Whether the activity has been passed or failed.',
                   required=False,
                   default=None)

    satisfied = Bool(title=u'Whether the activity has been satisfied.',
                     required=True)

    completed = Bool(title=u'Whether the activity has been completed.',
                     required=True)

    progress_status = Bool(title=u'The progress status.',
                           required=True)

    attempts = Number(title=u'The number of attempts.',
                      required=True)

    suspended = Bool(title=u'Whether the activity has been suspended.',
                     required=True)

    time = Number(title=u'The time spent on the activity.',
                   required=False,
                   default=None)

    score = Number(title=u'The activity score, from 0 to 1.',
                   required=False,
                   default=None)

    objectives = List(title=u'The activity objectives.',
                      required=True)

    children = List(title=u'The activity children.',
                    required=True)

    runtime = Object(ISCORMRuntime,
                     title=u'The activity runtime.',
                     required=False,
                     default=None)


class ISCORMRegistrationReport(interface.Interface):
    """
    An object containing high-level information about a registration result.
    """

    format = Choice(title=u'The results format.',
                    values=(u'course', u'activity', u'full'),
                    required=True)

    registration_id = ValidTextLine(title=u'The registration ID.',
                                    default=None,
                                    required=False)

    instance_id = ValidTextLine(title=u'The instance ID.',
                                default=None,
                                required=False)

    complete = Bool(title=u'Whether the registration has been completed.')

    success = Bool(title=u'Whether the registration has been passed or failed.')

    score = Number(title=u'The score, from 0 to 100.')

    total_time = Number(title=u'The total time tracked by the content player in seconds; \
                                that is, how long the learner had the course open.')

    activity = Object(ISCORMActivity,
                      title=u'A textual representation of registration activity in the course.',
                      required=False,
                      default=None)


class IUserRegistrationReportContainer(IContainer):
    """
    Contains :class:`ISCORMRegistrationReport` that have been generated by users in a SCORM SCO.
    """

    contains(ISCORMRegistrationReport)

    def add_registration_report(registration_report, user):
        """
        Adds a :class:`ISCORMRegistrationReport` to this container for the given :class:`IUser`.
        """

    def get_registration_report(user):
        """
        Returns the :class:`ISCORMRegistrationReport` from this container given a :class:`IUser`,
        or None if it does not exist.
        """

    def remove_registration_report(user):
        """
        Removes from this container the :class:`ISCORMRegistrationReport` for the given :class:`IUser`.
        """

class ISCORMRegistrationRemovedEvent(interface.Interface):
    """
    An event that is sent after a SCORM registration has been removed.
    """

    registration_id = ValidTextLine(title=u'The registration ID that was removed.',
                                    required=True)

    course = Object(ISCORMCourseInstance,
                    title=u'The course from which the registration was removed.',
                    required=True)

    user = Object(IUser,
                  title=u'The user for whom the registration was removed.',
                  required=True)


class ISCORMProgress(IProgress):
    """
    An :class:`IProgress` object for SCORM content.
    """

    registration_report = Object(ISCORMRegistrationReport,
                                 title=u'The SCORM registration report.',
                                 required=True)
    registration_report.setTaggedValue('_ext_excluded_out', True)


class ISCORMInteractionEvent(interface.Interface):
    """
    An event that is sent after an interaction with a SCORM package.
    """

    user = Object(IUser,
                  title=u'The user who launched the SCORM package.',
                  required=True)

    course = Object(ICourseInstance,
                    title=u'The course in which the SCORM package was launched.',
                    required=True)

    metadata = Object(ISCORMCourseMetadata,
                      title=u'The metadata object of the SCORM package that was launched.',
                      required=True)

    timestamp = DateTime(title=u'The time at which the SCORM package was launched.',
                         required=True)


@interface.implementer(ISCORMInteractionEvent)
class SCORMInteractionEvent(object):

    def __init__(self, user, course, metadata, timestamp):
        self.user = user
        self.course = course
        self.metadata = metadata
        self.timestamp = timestamp


class ISCORMPackageLaunchEvent(ISCORMInteractionEvent):
    """
    An event that is sent after a SCORM package has been launched.
    """


@interface.implementer(ISCORMPackageLaunchEvent)
class SCORMPackageLaunchEvent(SCORMInteractionEvent):
    pass


class ISCORMRegistrationPostbackEvent(ISCORMInteractionEvent):
    """
    An event that is sent after a SCORM registration postback is received.
    """


@interface.implementer(ISCORMRegistrationPostbackEvent)
class SCORMRegistrationPostbackEvent(SCORMInteractionEvent):
    pass
