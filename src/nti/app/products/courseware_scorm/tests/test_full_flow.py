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

from nti.app.products.courseware_scorm import SCORM_COLLECTION_NAME

from nti.app.products.courseware_scorm.client import SCORMCloudClient
from nti.app.products.courseware_scorm.client import PostBackURLGenerator
from nti.app.products.courseware_scorm.client import PostBackPasswordUtility

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.courses import SCORM_COURSE_MIME_TYPE

from nti.app.products.courseware_scorm.decorators import PROGRESS_REL

from nti.app.products.courseware_scorm.interfaces import ISCORMCourseMetadata
from nti.app.products.courseware_scorm.interfaces import ISCORMPackageLaunchEvent
from nti.app.products.courseware_scorm.interfaces import IRegistrationReportContainer
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


from nti.app.products.courseware_scorm.tests import CoursewareSCORMLayerTest

from nti.app.products.courseware_scorm.model import ScormContentInfo,\
    SCORMContentRef

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contenttypes.completion.interfaces import ICompletableItemCompletionPolicy

from nti.contenttypes.courses.courses import ContentCourseInstance

from nti.externalization.externalization import to_external_object
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfoContainer
from nti.app.products.courseware_scorm.interfaces import IRegistrationReportContainer
from nti.scorm_cloud.client.registration import RegistrationReport

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

    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.products.courseware_scorm.views.management_views.SCORMContentUploadMixin.upload_content')
    def test_full_flow(self, mock_upload_content):
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
                                'CreatedTime', not_none()))
        scorm_content_ntiid = scorm_content_ext.get('NTIID')
        assert_that(scorm_content_ntiid, not_none())
        # FIXME: Delete rel
        # FIXME: student, launch with no delete rel and progress rel
        self.require_link_href_with_rel(scorm_content_ext,
                                        LAUNCH_SCORM_COURSE_VIEW_NAME)

        # Create lesson content ref
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
        from IPython.terminal.debugger import set_trace;set_trace()



        postback_data_template = '''<?xml version="1.0" encoding="utf-8" ?>
        <rsp stat="ok">
        <registrationreport format="course" regid="%s" instanceid="0">
            <complete>complete</complete>
            <success>passed</success>
            <totaltime>326</totaltime>
            <score>100</score>
        </registrationreport>
        </rsp>'''

#         assert_that(self.registration_id, is_not(none()))
#         postback_data1 = postback_data_template % self.registration_id
#         params = {'username': self.h_username,
#                   'password': self.h_password,
#                   'data': postback_data1}
#         mock_do_on_scorm_registration_postback.expects_call()
#         self.testapp.post(self.postback_href,
#                           params=params,
#                           content_type='application/x-www-form-urlencoded')
#
#         report = RegistrationReport(format_=u'course',
#                                     regid=u'regid',
#                                     instanceid=u'instanceid',
#                                     complete=u'incomplete',
#                                     success=u'failure',
#                                     totaltime=3,
#                                     score=u'unknown')
#         container = IRegistrationReportContainer(course, None)
#         user_container = container.get(user.username)
#         if not user_container:
#             user_container = UserRegistrationReportContainer()
#             container[user.username] = user_container
#         notify(UserP)
