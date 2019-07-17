#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os

from six.moves import cStringIO

from zope import component
from zope import interface

from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfoContainer

from nti.contenttypes.courses.exporter import BaseSectionExporter

from nti.contenttypes.courses.interfaces import ICourseSectionExporter

from nti.contenttypes.presentation.interfaces import IAssetExportPostProcessor

from nti.namedfile.file import safe_filename

from nti.scorm_cloud.client.request import ScormCloudError


logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICourseSectionExporter)
class CourseSCORMPackageExporter(BaseSectionExporter):
    """
    Export scorm content into a `ScormContent` folder in the export. Each
    content will have a folder containing it's json data as well as a zip
    containing the scorm archive.
    """

    def get_archive(self, client, scorm_content):
        """
        Return the scorm content info referenced by the given scorm_id.
        """
        try:
            result = client.get_archive(scorm_content.scorm_id)
            result = cStringIO(result)
        except ScormCloudError:
            logger.exception("Scorm exception while exporting (%s) (%s)",
                             scorm_content.ntiid, scorm_content.scorm_id)
            result = None
        return result

    def export(self, course, filer, backup=True, salt=None):
        scorm_container = ISCORMContentInfoContainer(course, None)
        if not scorm_container:
            return
        client = component.queryUtility(ISCORMCloudClient)
        if client is None:
            logger.warn("Exporting SCORM content without client configured.")
            return
        bucket = self.course_bucket(course) or ''
        scorm_bucket = os.path.join(bucket, 'ScormContent')

        for scorm_content in scorm_container.values():
            logger.info("Exporting scorm content (%s) (%s)",
                        scorm_content.ntiid, scorm_content.scorm_id)
            scorm_archive = self.get_archive(client, scorm_content)
            if scorm_archive is not None:
                content_ntiid = scorm_content.ntiid
                if not backup:
                    content_ntiid = self.hash_ntiid(scorm_content.ntiid, salt)
                folder_name = safe_filename(content_ntiid)
                bucket = os.path.join(scorm_bucket, folder_name)
                zip_name = getattr(scorm_content.upload_job, 'UploadFilename', content_ntiid)
                zip_name = safe_filename(zip_name)
                filer.save(zip_name,
                           scorm_archive,
                           overwrite=True,
                           bucket=bucket,
                           contentType='application/zip; charset=UTF-8')
                # We not currently want to copy *any* scorm content state except for ntiid.
                # All of the other fields will be updated when the archive is uploaded to
                # scorm cloud.
                scorm_content_ext = {'NTIID': content_ntiid,
                                     'ScormArchiveFilename': zip_name}
                scorm_content_ext = self.dump(scorm_content_ext)
                filer.save('scorm_content.json',
                           scorm_content_ext,
                           overwrite=True,
                           bucket=bucket,
                           contentType="application/json")
        filer.default_bucket = None # restore


@component.adapter(ISCORMContentRef)
@interface.implementer(IAssetExportPostProcessor)
class ScormContentRefExportPostProcessor(object):

    def __init__(self, obj):
        self.ref = obj

    def process(self, exporter, asset, ext_obj, backup, salt):
        if not backup:
            ext_obj['target'] = exporter.hash_ntiid(asset.target, salt)
