#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import assert_that
does_not = is_not

import shutil

from zope import component

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.app.products.courseware_admin import VIEW_COURSE_ADMIN_LEVELS

from nti.app.products.courseware_scorm.views import CREATE_SCORM_COURSE_VIEW_NAME

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.dataserver.tests import mock_dataserver

from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


class TestManagementViews(ApplicationLayerTest):

    layer = PersistentInstructedCourseApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def tearDown(self):
        """
        Our janux.ou.edu site should have no courses in it.
        """
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
    def test_create_SCORM_course_view(self):
        """
        Validates SCORM course creation.
        """
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
        create_course_href = new_admin_href + '/' + CREATE_SCORM_COURSE_VIEW_NAME
        new_course = self.testapp.post_json(create_course_href,
                                            {'course': new_course_key,
                                             'title': new_course_key,
                                             'ProviderUniqueID': new_course_key})

        new_course = new_course.json_body
        new_course_href = new_course['href']
        course_delete_href = self.require_link_href_with_rel(new_course, 'delete')
        assert_that(new_course_href, not_none())
        assert_that(new_course[CLASS], is_('SCORMCourseInstance'))
        assert_that(new_course[MIMETYPE],
                    is_('application/vnd.nextthought.courses.courseinstance'))
        assert_that(new_course['NTIID'], not_none())
        assert_that(new_course['TotalEnrolledCount'], is_(0))

        catalog = self.testapp.get('%s/CourseCatalogEntry' % new_course_href)
        catalog = catalog.json_body
        entry_ntiid = catalog['NTIID']
        assert_that(entry_ntiid, not_none())

        # GUID NTIID
        assert_that(entry_ntiid,
                    is_not('tag:nextthought.com,2011-10:NTI-CourseInfo-Heisenberg_BreakingBad'))
        assert_that(catalog['ProviderUniqueID'], is_(new_course_key))

        # Delete
        self.testapp.delete(course_delete_href)
        self.testapp.get(new_course_href, status=404)
        courses = self.testapp.get(new_admin_href)
        assert_that(courses.json_body, does_not(has_item(new_course_key)))
        self.testapp.delete(new_admin_href)
