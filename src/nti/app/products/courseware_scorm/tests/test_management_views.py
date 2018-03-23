#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from collections import OrderedDict

import fudge

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
does_not = is_not

import shutil

from zope import component

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_admin import VIEW_COURSE_ADMIN_LEVELS

from nti.app.products.courseware_scorm.client import PostBackURLGenerator
from nti.app.products.courseware_scorm.client import PostBackPasswordUtility

from nti.app.products.courseware_scorm.courses import SCORM_COURSE_MIME_TYPE

from nti.app.products.courseware_scorm.decorators import PROGRESS_REL

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import IUserRegistrationReportContainer

from nti.app.products.courseware_scorm.tests import CoursewareSCORMTestLayer

from nti.app.products.courseware_scorm.views import GET_SCORM_ARCHIVE_VIEW_NAME
from nti.app.products.courseware_scorm.views import IMPORT_SCORM_COURSE_VIEW_NAME
from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager

from nti.dataserver.users.users import User

from nti.dataserver.tests import mock_dataserver

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.testing import externalizes

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.scorm_cloud.client.registration import RegistrationReport

HREF = StandardExternalFields().HREF
ITEMS = StandardExternalFields.ITEMS
CLASS = StandardExternalFields.CLASS
LINKS = StandardExternalFields.LINKS
MIMETYPE = StandardExternalFields.MIMETYPE

ARCHIVE_REL = GET_SCORM_ARCHIVE_VIEW_NAME
IMPORT_REL = IMPORT_SCORM_COURSE_VIEW_NAME
LAUNCH_REL = LAUNCH_SCORM_COURSE_VIEW_NAME


class TestManagementViews(ApplicationLayerTest):

    layer = CoursewareSCORMTestLayer

    default_origin = 'http://alpha.nextthought.com'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def tearDown(self):
        """
        Our janux.ou.edu site should have no courses in it.
        """
        with mock_dataserver.mock_db_trans(site_name='alpha.nextthought.com'):
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
                 'nti.app.products.courseware_scorm.client.SCORMCloudClient.delete_course',
                 'nti.app.products.courseware_scorm.client.SCORMCloudClient.enrollment_registration_exists',
                 'nti.app.products.courseware_scorm.tests.test_client.MockSCORMCloudService.get_registration_service')
    def test_create_SCORM_course_view(self, mock_has_scorm, mock_delete_course, mock_has_enrollment_reg, mock_get_registration_service):
        """
        Validates SCORM course creation.
        """
        mock_has_scorm.is_callable().returns(False)
        mock_has_enrollment_reg.is_callable().returns(True)
        
        mock_registration_service = fudge.Fake()
        mock_get_registration_service.is_callable().returns(mock_registration_service)

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

        mock_has_scorm.is_callable().returns(True)

        new_course = self.testapp.get(new_course_href).json_body
        assert_that(new_course, has_entry(LINKS, has_item(has_entry('rel', ARCHIVE_REL))))

        metadata = new_course[u'Metadata']
        assert_that(metadata, is_not(none()))
        assert_that(metadata, has_entry(LINKS, has_item(has_entry('rel', LAUNCH_REL))))

        catalog = self.testapp.get('%s/CourseCatalogEntry' % new_course_href)
        catalog = catalog.json_body
        entry_ntiid = catalog['NTIID']
        assert_that(entry_ntiid, not_none())
        
        course_ntiid = new_course['NTIID']
        
        new_username = u'CapnCook'
        
        with mock_dataserver.mock_db_trans():
            self._create_user(new_username)
            
        self.h_username, self.h_password = None, None
            
        # Check for SCORM progress Link on enrollment records
        self.progress_href = None
        self.postback_href = None
        new_username = u'CapnCook'
        with mock_dataserver.mock_db_trans(site_name='alpha.nextthought.com'):
            new_user = User.get_user(new_username)
            entry = find_object_with_ntiid(course_ntiid)
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
            
            self.h_username, self.h_password = PostBackPasswordUtility().credentials_for_enrollment(enrollment)
        
        assert_that(self.progress_href, is_not(none()))
        self.testapp.get(self.progress_href, status=403)
        
        reg_report = RegistrationReport(format_='course')
        mock_registration_service.expects('get_registration_result').returns(reg_report)
        new_user_env = self._make_extra_environ(new_username)
        progress = self.testapp.get(self.progress_href, extra_environ=new_user_env, status=200).json_body
        assert_that(progress, is_not(none()))
        assert_that(progress, has_entries('complete', False,
                                          'score', None,
                                          'success', False,
                                          'total_time', 0,
                                          'activity', None))
        self.progress_href = None
        
        postback_data = '''<?xml version="1.0" encoding="utf-8" ?>
        <rsp stat="ok">
        <registrationreport format="course" regid="8494706484070936189-5641550854418256038" instanceid="0">
            <complete>complete</complete>
            <success>passed</success>
            <totaltime>326</totaltime>
            <score>100</score>
        </registrationreport>
        </rsp>'''
         
        params = {'username': self.h_username,
                  'password': self.h_password,
                  'data': postback_data}
        self.testapp.post(self.postback_href, params=params, content_type='application/x-www-form-urlencoded')

        with mock_dataserver.mock_db_trans(site_name='alpha.nextthought.com'):
            new_user = User.get_user(new_username)
            entry = find_object_with_ntiid(course_ntiid)
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
            
        self.postback_href = None
        self.h_username, self.h_password = None, None

        # GUID NTIID
        assert_that(entry_ntiid,
                    is_not('tag:nextthought.com,2011-10:NTI-CourseInfo-Heisenberg_BreakingBad'))
        assert_that(catalog['ProviderUniqueID'], is_(new_course_key))

        # Delete
        mock_delete_course.expects_call()
        mock_registration_service.expects('deleteRegistration')
        self.testapp.delete(course_delete_href)
        self.testapp.get(new_course_href, status=404)
        courses = self.testapp.get(new_admin_href)
        assert_that(courses.json_body, does_not(has_item(new_course_key)))
        self.testapp.delete(new_admin_href)
