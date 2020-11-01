#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains general tests for tpDcc-libs-nameit
"""

from tpDcc.libs.unittests.core import unittestcase

from tpDcc.libs.nameit import __version__


class VersionTests(unittestcase.UnitTestCase(as_class=True), object):

    def test_version(self):
        assert __version__.get_version()
