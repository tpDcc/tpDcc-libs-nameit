#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains general tests for tpDcc-libs-nameit
"""

import pytest

from tpDcc.libs.nameit import __version__


def test_version():
    assert __version__.get_version()
