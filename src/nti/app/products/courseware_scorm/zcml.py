#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from functools import partial

from zope import interface

from zope.component.zcml import utility

from zope.configuration import fields

from nti.app.products.courseware_scorm.client import SCORMCloudClient

from nti.app.products.courseware_scorm.interfaces import ISCORMCloudClient

from nti.scorm_cloud.client import ScormCloudService

from nti.scorm_cloud.interfaces import IScormCloudService

logger = __import__('logging').getLogger(__name__)


class IRegisterSCORMCloudClient(interface.Interface):

    app_id = fields.TextLine(title=u'The SCORM Cloud app id.',
                             required=False,
                             default=u'')

    secret_key = fields.TextLine(title=u'The SCORM Cloud secret key.',
                                 required=False,
                                 default=u'')

    name = fields.TextLine(title=u'client identifier',
                           required=False,
                           default=u'')


def registerSCORMCloudClient(_context, app_id=u'', secret_key=u'', name=u''):
    factory = partial(SCORMCloudClient, app_id=app_id, secret_key=secret_key)
    utility(_context, provides=ISCORMCloudClient, factory=factory, name=name)


class IRegisterSCORMCloudService(interface.Interface):

    factory = fields.GlobalObject(title=u'The service factory that should be registered.',
                                  required=False)


def registerSCORMCloudService(_context, factory=ScormCloudService, name=u''):
    # The factory returns the class so the actual object can be constructed
    # using `withargs`
    utility(_context, provides=IScormCloudService,
            factory=lambda: factory, name=name)
