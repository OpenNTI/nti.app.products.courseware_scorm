#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

import fudge

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import equal_to
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import instance_of
from hamcrest import has_properties
does_not = is_not

import shutil

from webtest import Upload

from zope import component

from nti.app.contenttypes.completion.views import completed_items_link as make_completed_items_link

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_admin import VIEW_COURSE_ADMIN_LEVELS

from nti.app.products.courseware_scorm.client import SCORMCloudClient
from nti.app.products.courseware_scorm.client import PostBackURLGenerator
from nti.app.products.courseware_scorm.client import PostBackPasswordUtility

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.completion import _SCORMCompletableItemProvider

from nti.app.products.courseware_scorm.courses import SCORM_COURSE_MIME_TYPE

from nti.app.products.courseware_scorm.decorators import PROGRESS_REL

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import ISCORMPackageLaunchEvent
from nti.app.products.courseware_scorm.interfaces import ISCORMRegistrationPostbackEvent
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.app.products.courseware_scorm.utils import get_registration_id_for_user_and_course

from nti.app.products.courseware_scorm.views import GET_SCORM_ARCHIVE_VIEW_NAME
from nti.app.products.courseware_scorm.views import IMPORT_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import SYNC_REGISTRATION_REPORT_VIEW_NAME

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.contenttypes.completion.interfaces import IProgress
from nti.contenttypes.completion.interfaces import ICompletableItemCompletionPolicy
from nti.contenttypes.completion.interfaces import IPrincipalCompletedItemContainer
from nti.contenttypes.completion.interfaces import IRequiredCompletableItemProvider

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager

from nti.dataserver.users.users import User

from nti.dataserver.tests import mock_dataserver

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.testing import externalizes

from nti.links.externalization import render_link

from nti.links.links import Link

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.scorm_cloud.client.registration import Registration
from nti.scorm_cloud.client.registration import RegistrationReport

HREF = StandardExternalFields.HREF
ITEMS = StandardExternalFields.ITEMS
CLASS = StandardExternalFields.CLASS
LINKS = StandardExternalFields.LINKS
MIMETYPE = StandardExternalFields.MIMETYPE

ARCHIVE_REL = GET_SCORM_ARCHIVE_VIEW_NAME
IMPORT_REL = IMPORT_SCORM_COURSE_VIEW_NAME
LAUNCH_REL = LAUNCH_SCORM_COURSE_VIEW_NAME

logger = __import__('logging').getLogger(__name__)


def _do_on_scorm_package_launched():
    logger.debug('_scorm_package_launched')


@component.adapter(ISCORMPackageLaunchEvent)
def _scorm_package_launched(unused_event):
    _do_on_scorm_package_launched()


def _do_on_scorm_registration_postback():
    logger.debug('_on_scorm_registration_postback')


@component.adapter(ISCORMRegistrationPostbackEvent)
def _on_scorm_registration_postback(unused_event):
    _do_on_scorm_registration_postback()


def WithMockDSTrans(ds=None, site_name=None):
    def real_decorator(decorated_func):
        def wrapper(*args, **kwargs):
            with mock_dataserver.mock_db_trans(ds=ds, site_name=site_name):
                decorated_func(*args, **kwargs)
        return wrapper
    return real_decorator


class TestManagementViews(CoursewareSCORMLayerTest):

    default_origin = 'http://janux.ou.edu'

    def setUp(self):
        # A non-None client for tests
        self.client = SCORMCloudClient(app_id=u'app_id',
                                      secret_key=u'secret_key',
                                      service_url=u'service_url')
        component.getGlobalSiteManager().registerUtility(self.client, ISCORMCloudClient)

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def tearDown(self):
        """
        Our janux.ou.edu site should have no courses in it.
        """
        component.getGlobalSiteManager().unregisterUtility(self.client)
        with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
            library = component.getUtility(IContentPackageLibrary)
            enumeration = IDelimitedHierarchyContentPackageEnumeration(library)
            # pylint: disable=no-member
            shutil.rmtree(enumeration.root.absolute_path, True)

    def _get_admin_href(self):
        service_res = self.fetch_service_doc()
        workspaces = service_res.json_body['Items']
        courses_workspace = next(
            x for x in workspaces if x['Title'] == 'Courses'
        )
        admin_href = self.require_link_href_with_rel(courses_workspace,
                                                     VIEW_COURSE_ADMIN_LEVELS)
        return admin_href

    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.products.courseware_scorm.courses.SCORMCourseMetadata.has_scorm_package',
                 'nti.app.products.courseware_scorm.client.SCORMCloudClient.enrollment_registration_exists',
                 'nti.app.products.courseware_scorm.tests.test_client.MockSCORMCloudService.get_course_service',
                 'nti.app.products.courseware_scorm.tests.test_client.MockSCORMCloudService.get_tag_service',
                 'nti.app.products.courseware_scorm.tests.test_client.MockSCORMCloudService.get_registration_service',
                 'nti.app.products.courseware_scorm.tests.test_management_views._do_on_scorm_package_launched',
                 'nti.app.products.courseware_scorm.tests.test_management_views._do_on_scorm_registration_postback')
    def test_create_SCORM_course_view(self,
                                      mock_has_scorm,
                                      mock_has_enrollment_reg,
                                      mock_get_course_service,
                                      mock_get_tag_service,
                                      mock_get_registration_service,
                                      mock_do_on_scorm_package_launched,
                                      mock_do_on_scorm_registration_postback):
        """
        Validates SCORM course creation.
        """
        mock_has_scorm.is_callable().returns(False)
        mock_has_enrollment_reg.is_callable().returns(True)

        mock_course_service = fudge.Fake()
        mock_get_course_service.is_callable().returns(mock_course_service)

        mock_tag_service = fudge.Fake()
        mock_get_tag_service.is_callable().returns(mock_tag_service)

        mock_registration_service = fudge.Fake()
        mock_get_registration_service.is_callable().returns(mock_registration_service)
        mock_registration_service.provides('exists')

        admin_href = self._get_admin_href()

        # Create admin level
        test_admin_key = 'Heisenberg'
        self.testapp.post_json(admin_href, {'key': test_admin_key})
        admin_levels = self.testapp.get(admin_href)
        admin_levels = admin_levels.json_body
        new_admin = admin_levels[ITEMS][test_admin_key]
        new_admin_href = new_admin['href']

        assert_that(new_admin_href, not_none())

        new_course_key = 'BreakingBad'
        courses = self.testapp.get(new_admin_href)
        assert_that(courses.json_body, does_not(has_item(new_course_key)))

        # Create course
        create_course_href = new_admin_href
        new_course = self.testapp.post_json(create_course_href,
                                            {'course': new_course_key,
                                             'title': new_course_key,
                                             MIMETYPE: SCORM_COURSE_MIME_TYPE,
                                             'ProviderUniqueID': new_course_key})

        new_course = new_course.json_body
        new_course_href = new_course['href']
        course_delete_href = self.require_link_href_with_rel(new_course, 'delete')
        assert_that(new_course_href, not_none())
        assert_that(new_course[CLASS], is_('SCORMCourseInstance'))
        assert_that(new_course[MIMETYPE],
                    is_(SCORM_COURSE_MIME_TYPE))
        assert_that(new_course['NTIID'], not_none())
        assert_that(new_course['TotalEnrolledCount'], is_(0))
        assert_that(new_course, has_entry(LINKS, has_item(has_entry('rel', IMPORT_REL))))

        metadata = new_course[u'Metadata']
        assert_that(metadata, is_not(none()))
        assert_that(metadata[u'scorm_id'], is_(none()))
        assert_that(metadata, does_not(has_item(LINKS)))

        # Test import
        import_href = next((link for link in new_course[LINKS] if link['rel'] == IMPORT_REL), None)[HREF]
        assert_that(import_href, is_not(none()))
        mock_course_service.expects('import_uploaded_course')
        mock_tag_service.expects('set_scorm_tags')
        self.testapp.post(import_href, params=[('source', Upload('scorm.zip', b'data', 'application/zip'))])

        mock_has_scorm.is_callable().returns(True)

        new_course = self.testapp.get(new_course_href).json_body
        assert_that(new_course, has_entry(LINKS, has_item(has_entry('rel', ARCHIVE_REL))))

        metadata = new_course[u'Metadata']
        assert_that(metadata, is_not(none()))
        scorm_id = metadata.get('scorm_id')
        assert_that(scorm_id, not_none())
        assert_that(metadata, has_entry(LINKS, has_item(has_entry('rel', LAUNCH_REL))))

        catalog_entry_href = '%s/CourseCatalogEntry' % new_course_href
        catalog = self.testapp.get(catalog_entry_href)
        catalog = catalog.json_body
        entry_ntiid = catalog['NTIID']
        assert_that(entry_ntiid, not_none())

        with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
            # Ensure no default outline
            entry = find_object_with_ntiid(entry_ntiid)
            course = ICourseInstance(entry)
            assert_that(course.Outline, has_length(0))

        self.course_ntiid = new_course['NTIID']

        # Disable preview mode
        catalog_edit_href = next((link for link in catalog[LINKS] if link['rel'] == u'edit'), None)[HREF]
        catalog_edit_params = {u'Preview': False}
        self.testapp.put_json(catalog_edit_href, params=catalog_edit_params)
        catalog = self.testapp.get(catalog_entry_href).json_body
        assert_that(catalog[u'Preview'], is_(False))

        new_username1 = u'CapnCook'
        new_username2 = u'Krazy-8'

        with mock_dataserver.mock_db_trans():
            self._create_user(new_username1)
            self._create_user(new_username2)

        new_user_env = self._make_extra_environ(new_username1)

        self.progress_href = None
        self.postback_href = None
        self.completed_items_href = None
        self.registration_id = None
        self.h_username, self.h_password = None, None

        # Check for SCORM progress Link on enrollment records
        self._test_enrollment_links(new_username1)

        # Test launch
        new_course = self.testapp.get(new_course_href, extra_environ=new_user_env).json_body
        metadata = new_course[u'Metadata']
        launch_href = next((link for link in metadata[LINKS] if link['rel'] == LAUNCH_REL), None)[HREF]
        mock_do_on_scorm_package_launched.expects_call()
        mock_registration_service.expects('createRegistration')
        mock_registration_service.expects('launch').returns(self.default_origin)
        self.testapp.get(launch_href, extra_environ=new_user_env, status=303)

        assert_that(self.progress_href, is_not(none()))
        self.testapp.get(self.progress_href, status=403)

        # Test import-replace
        assert_that(self.registration_id, is_not(none()))
        registration = Registration(appId=u'appId',
                                    registrationId=self.registration_id,
                                    courseId=u'courseId')
        mock_registration_service.provides('getRegistrationList').returns([registration])
        mock_registration_service.expects('deleteRegistration')
        self.testapp.post(import_href, params=[('source', Upload('scorm.zip', b'data', 'application/zip')),
                                               ('reset-registrations', True)])

        reg_report = RegistrationReport(format_='course')
        mock_registration_service.expects('get_registration_result').returns(reg_report)
        progress = self.testapp.get(self.progress_href, extra_environ=new_user_env, status=200).json_body
        assert_that(progress, is_not(none()))
        assert_that(progress, has_entries('complete', False,
                                          'score', None,
                                          'success', False,
                                          'total_time', 0,
                                          'activity', None))
        self.progress_href = None

        postback_data_template = '''<?xml version="1.0" encoding="utf-8" ?>
        <rsp stat="ok">
        <registrationreport format="course" regid="%s" instanceid="0">
            <complete>complete</complete>
            <success>passed</success>
            <totaltime>326</totaltime>
            <score>100</score>
        </registrationreport>
        </rsp>'''

        assert_that(self.registration_id, is_not(none()))
        postback_data1 = postback_data_template % self.registration_id
        params = {'username': self.h_username,
                  'password': self.h_password,
                  'data': postback_data1}
        mock_do_on_scorm_registration_postback.expects_call()
        self.testapp.post(self.postback_href,
                          params=params,
                          content_type='application/x-www-form-urlencoded')

        self._test_completion_providers(new_username1, mock_has_scorm)

        # CompletedItems link
        completed_items = self.testapp.get(self.completed_items_href).json_body['Items']
        assert_that(completed_items, has_length(1))

        self.postback_href = None
        self.completed_items_href = None
        self.h_username, self.h_password = None, None
        self.registration_id = None

        self.sync_report_href = None
        self._get_completed_items_href(new_username2)

        # Post to SyncRegistrationReport href
        self.testapp.post(self.sync_report_href)

        # Test CompletedItems
        completed_items = self.testapp.get(self.completed_items_href).json_body['Items']
        assert_that(completed_items, has_length(0))

        self._test_registration_report_container(new_username2, mock_registration_service)

        self.completed_items_href = None
        self.sync_report_href = None

        # GUID NTIID
        assert_that(entry_ntiid,
                    is_not('tag:nextthought.com,2011-10:NTI-CourseInfo-Heisenberg_BreakingBad'))
        assert_that(catalog['ProviderUniqueID'], is_(new_course_key))

        # Delete
        mock_course_service.expects('delete_course')
        self.testapp.delete(course_delete_href)
        self.testapp.get(new_course_href, status=404)
        courses = self.testapp.get(new_admin_href)
        assert_that(courses.json_body, does_not(has_item(new_course_key)))
        self.testapp.delete(new_admin_href)
        self.course_ntiid = None

    @WithMockDSTrans(site_name='janux.ou.edu')
    def _test_enrollment_links(self, username, scorm_id):
        new_user = User.get_user(username)
        entry = find_object_with_ntiid(self.course_ntiid)
        course = ICourseInstance(entry)

        enrollment_manager = ICourseEnrollmentManager(course)
        enrollment_record = enrollment_manager.enroll(new_user)
        enrollment = ICourseInstanceEnrollment(enrollment_record)
        assert_that(enrollment, is_not(none()))
        assert_that(enrollment,
                    externalizes(has_entry(LINKS, has_item(has_entry('rel', PROGRESS_REL)))))

        ext_enrollment = toExternalObject(enrollment)
        progress_link = next((link for link in ext_enrollment[LINKS] if link['rel'] == PROGRESS_REL), None)
        assert_that(progress_link, is_not(none()))
        self.progress_href = progress_link[HREF]

        postback_url_generator = PostBackURLGenerator()
        mock_request = fudge.Fake().provides('relative_url').calls(lambda url: url)
        self.postback_href = postback_url_generator.url_for_registration_postback(enrollment, mock_request)

        # Manually create link until we know why it isn't being decorated in the test
        completed_items_link = make_completed_items_link(course, new_user)
        assert_that(completed_items_link, is_not(none()))
        self.completed_items_href = render_link(completed_items_link)[HREF]

        self.h_username, self.h_password = PostBackPasswordUtility().credentials_for_enrollment(enrollment)
        self.registration_id = get_registration_id_for_user_and_course(scorm_id, new_user, course)

    @WithMockDSTrans(site_name='janux.ou.edu')
    def _test_completion_providers(self, username, mock_has_scorm):
        new_user = User.get_user(username)
        entry = find_object_with_ntiid(self.course_ntiid)
        course = ICourseInstance(entry)
        metadata = ISCORMCourseMetadata(course)
        container = IUserRegistrationReportContainer(metadata)
        report = container.get_registration_report(new_user)
        assert_that(report, is_not(none()))
        assert_that(report,
                    externalizes(has_entries(u'complete', True,
                                             u'success', True,
                                             u'score', 100,
                                             u'total_time', 326)))

        # Completable item providers
        providers = component.subscribers((course,),
                                              IRequiredCompletableItemProvider)
        assert_that(len(providers), is_not(0))
        assert_that(providers, has_item(instance_of(_SCORMCompletableItemProvider)))
        for provider in providers:
            if type(provider) is _SCORMCompletableItemProvider:
                mock_has_scorm.is_callable().returns(False)
                assert_that(provider.iter_items(new_user), does_not(has_item(metadata)))
                mock_has_scorm.is_callable().returns(True)
                assert_that(provider.iter_items(new_user), has_item(metadata))

        # Test progress
        progress = component.queryMultiAdapter((new_user, metadata, course),
                                                IProgress)
        assert_that(progress, is_not(none()))
        assert_that(progress,
                    has_properties(u'AbsoluteProgress', 1,
                                   u'HasProgress', True,
                                   u'MaxPossibleProgress', 1))

        # Test completion policy
        policy = component.getMultiAdapter((metadata, course),
                                            ICompletableItemCompletionPolicy)
        assert_that(policy, is_not(none()))
        completed_item = policy.is_complete(progress)
        assert_that(completed_item, is_not(none()))
        assert_that(completed_item.CompletedDate, equal_to(progress.LastModified))

        # Test that the completed item container has a completed item
        container = component.queryMultiAdapter((new_user, course),
                                                IPrincipalCompletedItemContainer)
        completed_item = container.get_completed_item(metadata)
        assert_that(completed_item, is_not(none()))

    @WithMockDSTrans(site_name='janux.ou.edu')
    def _get_completed_items_href(self, username):
        new_user = User.get_user(username)
        entry = find_object_with_ntiid(self.course_ntiid)
        course = ICourseInstance(entry)

        # Get SyncRegistrationReport href
        enrollment_manager = ICourseEnrollmentManager(course)
        enrollment_record = enrollment_manager.enroll(new_user)
        enrollment = ICourseInstanceEnrollment(enrollment_record)
        self.sync_report_href = render_link(Link(enrollment,
                                                 rel=SYNC_REGISTRATION_REPORT_VIEW_NAME,
                                                 elements=(SYNC_REGISTRATION_REPORT_VIEW_NAME,)))[HREF]

        # Manually create link until we know why it isn't being decorated in the test
        completed_items_link = make_completed_items_link(course, new_user)
        assert_that(completed_items_link, is_not(none()))
        self.completed_items_href = render_link(completed_items_link)[HREF]

    @WithMockDSTrans(site_name='janux.ou.edu')
    def _test_registration_report_container(self, username, mock_registration_service):
        new_user = User.get_user(username)
        entry = find_object_with_ntiid(self.course_ntiid)
        course = ICourseInstance(entry)

        # Make sure registration report was synced
        metadata = ISCORMCourseMetadata(course)
        container = IUserRegistrationReportContainer(metadata)
        report = container.get_registration_report(new_user)
        assert_that(report, is_not(none()))
        assert_that(report,
                    externalizes(has_entries(u'complete', False,
                                             u'score', None,
                                             u'success', False,
                                             u'total_time', 0,
                                             u'activity', None)))

        # We do not remove reports when deleting
        mock_registration_service.expects('deleteRegistration')
        enrollment_manager = ICourseEnrollmentManager(course)
        enrollment_manager.drop(new_user)
        report = container.get_registration_report(new_user)
        assert_that(report, is_not(none()))
