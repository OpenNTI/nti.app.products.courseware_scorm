#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.app.products.courseware_scorm.interfaces import ISCORMIdentifier

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
