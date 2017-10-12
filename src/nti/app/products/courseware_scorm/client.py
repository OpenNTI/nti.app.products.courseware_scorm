#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.app.products.courseware_scorm.zcml import ISCORMClient


@interface.implementer(ISCORMClient)
class SCORMClient(object):
    """
    The default SCORM client.
    """
