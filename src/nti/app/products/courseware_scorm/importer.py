#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import simplejson

from zope import component
from zope import interface

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.utils import upload_scorm_content_async

from nti.cabinet.filer import transfer_to_native_file

from nti.contentlibrary.interfaces import IFilesystemBucket

from nti.contenttypes.courses.importer import BaseSectionImporter

from nti.contenttypes.courses.interfaces import ICourseSectionImporter

from nti.scorm_cloud.client.request import ScormCloudError

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICourseSectionImporter)
class CourseSCORMPackageImporter(BaseSectionImporter):

    def _get_scorm_content_ext(self, content_bucket):
        scorm_content_file = content_bucket.getChildNamed('scorm_content.json')
        if scorm_content_file is not None:
            scorm_content = scorm_content_file.readContents()
            scorm_content = scorm_content.decode('utf-8') if isinstance(scorm_content, bytes) else scorm_content
            return simplejson.loads(scorm_content)

    def process(self, course, filer, writeout=True):
        path = self.course_bucket_path(course) + 'ScormContent'
        client = component.queryUtility(ISCORMCloudClient)
        if client is None:
            logger.warn("Importing SCORM content without client configured.")
            return
        if filer.is_bucket(path):
            content_buckets = filer.get(path)
            for content_bucket_name in content_buckets.enumerateChildren() or ():
                content_bucket = content_buckets.getChildNamed(content_bucket_name)
                scorm_content_ext = self._get_scorm_content_ext(content_bucket)
                if scorm_content_ext is None:
                    logger.warn("No scorm json found (%s)", content_bucket_name)
                    continue
                scorm_content_ntiid = scorm_content_ext.get('NTIID')
                scorm_archive_name = scorm_content_ext.get('ScormArchiveFilename')
                if not scorm_content_ntiid or not scorm_archive_name:
                    logger.warn("Invalid scorm json (%s)", scorm_content_ext)
                    continue
                scorm_archive = content_bucket.getChildNamed(scorm_archive_name)
                if scorm_archive is None:
                    logger.warn("No scorm archive found (%s/%s)", content_bucket, scorm_archive_name)
                    continue

                try:
                    # Ok, we're good to upldate; ensure we use the ntiid we have
                    upload_scorm_content_async(scorm_archive, client, ntiid=scorm_content_ntiid)
                except ScormCloudError:
                    logger.exception("Scorm exception while uplading (%s)",
                                     scorm_content_ntiid)
                else:
                    # Save source
                    if writeout and IFilesystemBucket.providedBy(course.root):
                        scorm_archive = content_bucket.getChildNamed(scorm_archive_name)
                        if scorm_archive is not None:
                            self.makedirs(course.root.absolute_path)
                            new_path = os.path.join(course.root.absolute_path,
                                                    'ScormContent',
                                                    scorm_archive_name)
                            transfer_to_native_file(scorm_archive, new_path)
