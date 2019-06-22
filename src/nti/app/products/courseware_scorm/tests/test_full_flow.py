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
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
does_not = is_not

import shutil

from webtest import Upload

from zope import component

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.courseware_admin import VIEW_COURSE_ADMIN_LEVELS

from nti.app.products.courseware_scorm import SCORM_COLLECTION_NAME

from nti.app.products.courseware_scorm.client import SCORMCloudClient
from nti.app.products.courseware_scorm.client import PostBackURLGenerator
from nti.app.products.courseware_scorm.client import PostBackPasswordUtility

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.model import SCORMContentRef
from nti.app.products.courseware_scorm.model import ScormContentInfo

from nti.app.products.courseware_scorm.utils import get_registration_id_for_user_and_course

from nti.app.products.courseware_scorm.views import LAUNCH_SCORM_COURSE_VIEW_NAME

from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager

from nti.dataserver.tests import mock_dataserver

from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids.ntiids import find_object_with_ntiid

HREF = StandardExternalFields.HREF
ITEMS = StandardExternalFields.ITEMS
CLASS = StandardExternalFields.CLASS
LINKS = StandardExternalFields.LINKS
MIMETYPE = StandardExternalFields.MIMETYPE

LAUNCH_REL = LAUNCH_SCORM_COURSE_VIEW_NAME

logger = __import__('logging').getLogger(__name__)


class TestFullFlow(CoursewareSCORMLayerTest):

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

    def _create_course(self):
        """
        Create a course, returning the ext course.
        """
        # Create admin level
        test_admin_key = 'Heisenberg'
        admin_href = self._get_admin_href()
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
                                             'ProviderUniqueID': new_course_key})

        new_course = new_course.json_body
        return new_course

    def _create_scorm_content_ref(self, scorm_content_ntiid, outline):
        """
        Create a ScormContentRef given the scorm content ntiid, returning
        the newly created ScormContentRef.
        """
        outline_contents_href = self.require_link_href_with_rel(outline, 'contents')
        outline_res = self.testapp.get(outline_contents_href).json_body
        lesson_node = outline_res[0]['contents'][0]
        lesson_content_href = self.require_link_href_with_rel(lesson_node,
                                                              "overview-content")
        lesson_ext = self.testapp.get(lesson_content_href).json_body
        group_ext = lesson_ext['Items'][0]
        group_put_href = self.require_link_href_with_rel(group_ext,
                                                         "ordered-contents")
        scorm_ref_data = {"MimeType": SCORMContentRef.mime_type,
                          "title": u'scorm content title',
                          "description": u'scorm description',
                          "target": scorm_content_ntiid}
        scorm_ref_ext = self.testapp.post_json(group_put_href, scorm_ref_data)
        return scorm_ref_ext.json_body

    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.products.courseware_scorm.views.management_views.SCORMContentUploadMixin.upload_content')
    def test_full_flow(self, mock_upload_content):
        """
        Create scorm content, including a ref in a lesson. Validate
        editor and enrolled user interaction (including completion)
        with the content.
        """
        new_course = self._create_course()
        new_course_href = new_course['href']
        outline = new_course['Outline']
        scorm_collection_href = self.require_link_href_with_rel(new_course, SCORM_COLLECTION_NAME)

        res = self.testapp.get(scorm_collection_href).json_body
        assert_that(res['Items'], has_length(0))
        assert_that(res['Total'], is_(0))

        # Upload content
        content_info = ScormContentInfo(scorm_id=u'new-scorm-id')
        mock_upload_content.is_callable().returns(content_info)
        res = self.testapp.put(scorm_collection_href,
                               params=[('source', Upload('scorm.zip', b'data', 'application/zip'))])

        res = self.testapp.get(scorm_collection_href).json_body
        assert_that(res['Items'], has_length(1))
        assert_that(res['Total'], is_(1))
        scorm_content_ext = res['Items'][0]
        assert_that(scorm_content_ext,
                    has_entries('scorm_id', 'new-scorm-id',
                                'Creator', u'sjohnson@nextthought.com',
                                'CreatedTime', not_none()))
        scorm_content_ntiid = scorm_content_ext.get('NTIID')
        assert_that(scorm_content_ntiid, not_none())
        # FIXME: student, launch with no delete rel and progress rel
        self.require_link_href_with_rel(scorm_content_ext, 'delete')
        self.require_link_href_with_rel(scorm_content_ext,
                                        LAUNCH_SCORM_COURSE_VIEW_NAME)

        # Create lesson content ref
        scorm_ref_ext = self._create_scorm_content_ref(scorm_content_ntiid, outline)
        assert_that(scorm_ref_ext, has_entries(u'CompletedDate', none(),
                                               u'CompletedItem', none(),
                                               u'CompletionPolicy', none()))

        assert_that(scorm_ref_ext, has_entries(u'description', u'scorm description',
                                               u'href', not_none(),
                                               u'icon', none(),
                                               u'ntiid', not_none(),
                                               u'target', scorm_content_ntiid,
                                               u'title', u'scorm content title',
                                               u'MimeType', u'application/vnd.nextthought.scormcontentref',
                                               u'CreatedTime', not_none(),
                                               u'Creator', u'sjohnson@nextthought.com',
                                               u'Last Modified', not_none()))
        scorm_ref_href = scorm_ref_ext['href']
        self.require_link_href_with_rel(scorm_ref_ext, 'edit')
        scorm_ref_content = scorm_ref_ext.get('ScormContentInfo')
        assert_that(scorm_ref_content, not_none())
        assert_that(scorm_ref_content, has_entry('NTIID', scorm_content_ntiid))

        # Create enrolled user, reg_id and postback url
        new_username1 = u'CapnCook'
        with mock_dataserver.mock_db_trans():
            new_user = self._create_user(new_username1)
            course = find_object_with_ntiid(new_course['NTIID'])
            enrollment_manager = ICourseEnrollmentManager(course)
            enrollment_record = enrollment_manager.enroll(new_user)
            enrollment = ICourseInstanceEnrollment(enrollment_record)
            reg_id = get_registration_id_for_user_and_course('new-scorm-id', new_user, course)
            postback_util = PostBackPasswordUtility()
            username_hash, pw_hash = postback_util.credentials_for_enrollment(enrollment)
            postback_url_generator = PostBackURLGenerator()
            mock_request = fudge.Fake().provides('relative_url').calls(lambda url: url)
            postback_href = postback_url_generator.url_for_registration_postback(enrollment, mock_request)

        assert_that(reg_id, not_none())
        assert_that(postback_href, not_none())
        new_user_env = self._make_extra_environ(new_username1)

        # Validate enrolled user rels
        user_course_ext = self.testapp.get(new_course_href, extra_environ=new_user_env)
        user_course_ext = user_course_ext.json_body
        self.forbid_link_with_rel(user_course_ext, SCORM_COLLECTION_NAME)

        user_scorm_ref_ext = self.testapp.get(scorm_ref_href, extra_environ=new_user_env)
        user_scorm_ref_ext = user_scorm_ref_ext.json_body
        self.forbid_link_with_rel(user_scorm_ref_ext, 'edit')

        user_scorm_content_ext = user_scorm_ref_ext.get('ScormContentInfo')
        assert_that(user_scorm_content_ext, not_none())
        assert_that(user_scorm_content_ext, has_entry('NTIID', scorm_content_ntiid))
        self.require_link_href_with_rel(user_scorm_content_ext,
                                        LAUNCH_SCORM_COURSE_VIEW_NAME)
        self.forbid_link_with_rel(user_scorm_content_ext, 'delete')

        # Validate postback
        def _get_postback(reg_id, complete=True, success=True):
            is_success = 'passed' if success else 'failed'
            is_complete = 'complete' if complete else 'incomplete'
            postback_data_template = '''<?xml version="1.0" encoding="utf-8" ?>
                <rsp stat="ok">
                <registrationreport format="course" regid="%s" instanceid="0">
                    <complete>%s</complete>
                    <success>%s</success>
                    <totaltime>326</totaltime>
                    <score>100</score>
                </registrationreport>
                </rsp>'''
            return postback_data_template % (reg_id, is_complete, is_success)

        postback_data = _get_postback(reg_id)
        # Test bad data/input
        params = {'username': username_hash + 'bleh',
                  'password': pw_hash,
                  'data': postback_data}
        self.testapp.post(postback_href,
                          params=params,
                          content_type='application/x-www-form-urlencoded',
                          status=403)

        params = {'username': username_hash,
                  'password': pw_hash + 'xxx',
                  'data': postback_data}
        self.testapp.post(postback_href,
                          params=params,
                          content_type='application/x-www-form-urlencoded',
                          status=403)

        bad_regid = '%s%s' % (reg_id, '1111')
        bad_postback_data = _get_postback(bad_regid)
        params = {'username': username_hash,
                  'password': pw_hash,
                  'data': bad_postback_data}
        self.testapp.post(postback_href,
                          params=params,
                          content_type='application/x-www-form-urlencoded',
                          status=400)

        # Incomplete postback
        incomplete_postback_data = _get_postback(reg_id, complete=False)
        params = {'username': username_hash,
                  'password': pw_hash,
                  'data': incomplete_postback_data}
        self.testapp.post(postback_href,
                          params=params,
                          content_type='application/x-www-form-urlencoded')
        user_scorm_ref_ext = self.testapp.get(scorm_ref_href, extra_environ=new_user_env)
        user_scorm_ref_ext = user_scorm_ref_ext.json_body
        user_scorm_content_ext = user_scorm_ref_ext.get('ScormContentInfo')
        assert_that(user_scorm_content_ext, not_none())

        failed_postback_data = _get_postback(reg_id, complete=True, success=False)
        params = {'username': username_hash,
                  'password': pw_hash,
                  'data': failed_postback_data}
        self.testapp.post(postback_href,
                          params=params,
                          content_type='application/x-www-form-urlencoded')
