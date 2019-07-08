#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import gevent
import transaction

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.app.products.courseware_scorm.interfaces import UPLOAD_CREATED

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier
from nti.app.products.courseware_scorm.interfaces import ISCORMContentRef
from nti.app.products.courseware_scorm.interfaces import ISCORMContentInfo
from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.app.products.courseware_scorm.model import ScormContentInfo
from nti.app.products.courseware_scorm.model import SCORMContentInfoUploadJob

from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contenttypes.courses.common import get_course_packages

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.courses.utils import get_parent_course

from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.scorm_cloud.client.request import ScormCloudError

from nti.site.site import get_site_for_site_names
from nti.site.site import get_component_hierarchy_names

from nti.site.utils import registerUtility

logger = __import__('logging').getLogger(__name__)


def get_registration_id_for_user_and_course(scorm_id, user, course):
    """
    The user's enrollment record ds_intid and the scorm id, separated
    by an underscore.
    """
    identifier = component.getMultiAdapter((user, course),
                                            ISCORMIdentifier)
    return '%s_%s' % (identifier.get_id(), scorm_id)


def parse_registration_id(registration_id):
    """
    Split the registration_id into the user's enrollment record ds_intid and
    the scorm id.
    """
    return registration_id.split('_')


def _pkg_containers(package):
    result = []
    def recur(unit):
        for child in unit.children or ():
            recur(child)
        result.append(unit.ntiid)
    recur(package)
    return result


def _course_containers(course):
    result = set()
    courses = {course, get_parent_course(course)}
    courses.discard(None)
    for _course in courses:
        entry = ICourseCatalogEntry(_course)
        for package in get_course_packages(_course):
            result.update(_pkg_containers(package))
        result.add(entry.ntiid)
    return result


def get_scorm_refs(course, scorm_id):
    """
    Return all scorm content refs in lessons in our course, returning
    the collection that matches the given scorm_id.
    """
    catalog = get_library_catalog()
    intids = component.getUtility(IIntIds)
    container_ntiids = _course_containers(course)
    result = []
    for item in catalog.search_objects(intids=intids,
                                       container_all_of=False,
                                       container_ntiids=container_ntiids,
                                       sites=get_component_hierarchy_names(),
                                       provided=(ISCORMContentRef,)):
        if item.scorm_id == scorm_id:
            result.append(item)
    return result


def _upload_scorm_content(client, source):
    return client.import_scorm_content_async(source)


def upload_scorm_content_async(source, client=None, ntiid=None):
    """
    Upload the content asynchronously to scorm cloud.

    Returns the newly created :class:`IScormContentInfo`.

    The `ntiid` can overwrite the generated ScormContentInfo, useful
    to fix that value during import.
    """
    if not client:
        client = component.queryUtility(ISCORMCloudClient)
    token, scorm_id = _upload_scorm_content(client, source)
    result = ScormContentInfo(scorm_id=scorm_id)
    if ntiid is not None:
        result.ntiid = ntiid
    result.upload_job = SCORMContentInfoUploadJob(Token=token,
                                                  State=UPLOAD_CREATED,
                                                  UploadFilename=source.filename)
    registerUtility(component.getSiteManager(),
                    result,
                    ISCORMContentInfo,
                    name=result.ntiid)
    _spawn_async_job_updater(result)
    return result


def _copy_scorm_content_info(source, target):
    for name in ISCORMContentInfo.names():
        value = getattr(source, name, None)
        if value is not None:
            setattr(target, name, value)


def _update_upload_job(upload_job, async_result):
    upload_job.ErrorMessage = async_result.error_message
    upload_job.State = async_result.status


def _get_async_result(client, token):
    return client.get_async_import_result(token)


def _get_scorm_content(client, scorm_id):
    return client.get_scorm_instance_detail(scorm_id)


def _set_scorm_content_tags(client, scorm_id, tags):
    return client.set_scorm_tags(scorm_id,
                                 tags)


def check_and_update_scorm_content_info(content_info, client=None):
    """
    Fetch the given :class:`IScormContentInfo` async import status,
    updating the content_info if necessary.

    Returns a bool if state was updated.
    """
    result = False
    if not client:
        client = component.queryUtility(ISCORMCloudClient)
    upload_job = content_info.upload_job
    # Fetch job status
    async_result = _get_async_result(client, upload_job.token)
    if async_result.status != upload_job.State:
        result = True
        # State has changed, we need to update and commit.
        _update_upload_job(upload_job, async_result)
        if upload_job.is_upload_successfully_complete():
            logger.debug("Updating scorm state (%s) (%s) (%s)",
                         upload_job.State, async_result.status, upload_job.ErrorMessage)
            new_content_info = _get_scorm_content(client, content_info.scorm_id)
            # Collection has tag info
            _set_scorm_content_tags(client,
                                    content_info.scorm_id,
                                    content_info.__parent__.tags)
            # Copy our non-null attributes from scorm cloud info
            # into our context.
            _copy_scorm_content_info(new_content_info, content_info)
    return result


def _spawn_async_job_updater(content_info):
    """
    Spawn a greenlet to update the given :class:`IScormContentInfo`.
    """
    tx_runner = component.getUtility(IDataserverTransactionRunner)
    content_info_ntiid = content_info.ntiid
    content_site_name = getSite().__name__
    def do_update_scorm_content():
        keep_running = True
        while keep_running:
            def _check_state():
                """
                Check and update, returning whether we need to check again.
                We run until our job is complete or an error occurs.
                """
                content_site = get_site_for_site_names((content_site_name,))
                with current_site(content_site):
                    keep_running_result = True
                    # Validate still have object to check
                    tx_content_info = find_object_with_ntiid(content_info_ntiid)
                    if tx_content_info is None:
                        keep_running_result = False
                        return keep_running_result
                    # Validate not updated by someone else
                    upload_job = tx_content_info.upload_job
                    is_complete = upload_job.is_upload_complete()
                    if is_complete:
                        keep_running_result = False
                        return keep_running_result
                    try:
                        check_and_update_scorm_content_info(tx_content_info)
                    except ScormCloudError:
                        # We cannot do anything here right?
                        logger.exception('Scorm error while updating (%s) (%s)',
                                         content_info_ntiid, tx_content_info.scorm_id)
                        keep_running_result = False
                    # Check if we are now complete
                    if upload_job.is_upload_complete():
                        keep_running_result = False
                    return keep_running_result
            # Only update condition if successful tx
            keep_running = tx_runner(_check_state, retries=5, sleep=0.1)
            gevent.sleep(60)
    def hook(s): return s and gevent.spawn(do_update_scorm_content)
    transaction.get().addAfterCommitHook(hook)
