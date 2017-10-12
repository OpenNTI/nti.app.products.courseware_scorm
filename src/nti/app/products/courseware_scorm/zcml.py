#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope import interface

from zope.component.zcml import utility

from zope.configuration import fields

from nti.app.products.courseware_scorm.client import SCORMClient


class ISCORMClient(interface.Interface):
    """
    A client interface for SCORM operations.
    """


def registerSCORMClient(_context, name=''):
    factory = SCORMClient
    utility(_context, provides=ISCORMClient, factory=factory, name=name)
