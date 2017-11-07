#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from functools import partial

from zope import interface

from zope.component.zcml import utility

from zope.configuration import fields

from nti.app.products.courseware_scorm.client import SCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

logger = __import__('logging').getLogger(__name__)


class IRegisterSCORMCloudClient(interface.Interface):

    name = fields.TextLine(title=u"client identifier",
                           required=False,
                           default=u'')


def registerSCORMCloudClient(_context, name=''):
    factory = partial(SCORMCloudClient)
    utility(_context, provides=ISCORMCloudClient, factory=factory, name=name)
