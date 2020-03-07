#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc-libs-nameit
"""

from __future__ import print_function, division, absolute_import

import os
import inspect
import logging.config


def init(do_reload=False, dev=False):
    """
    Initializes module
    :param do_reload: bool, Whether to reload modules or not
    :param dev: bool, Whether artellapipe is initialized in dev mode or not
    """

    from tpDcc.libs.nameit import register
    from tpDcc.libs.python import importer

    logger = create_logger()

    class tpNameIt(importer.Importer, object):
        def __init__(self, *args, **kwargs):
            super(tpNameIt, self).__init__(module_name='tpDcc.libs.nameit', *args, **kwargs)

        def get_module_path(self):
            """
            Returns path where tpNameIt module is stored
            :return: str
            """

            try:
                mod_dir = os.path.dirname(inspect.getframeinfo(inspect.currentframe()).filename)
            except Exception:
                try:
                    mod_dir = os.path.dirname(__file__)
                except Exception:
                    try:
                        import tpDcc.libs.nameit
                        mod_dir = tpDcc.libs.nameit.__path__[0]
                    except Exception:
                        return None

            return mod_dir

    tpnameit_importer = importer.init_importer(importer_class=tpNameIt, do_reload=False)

    register.register_class('logger', logger)

    tpnameit_importer.import_modules()
    tpnameit_importer.import_packages(only_packages=True)
    if do_reload:
        tpnameit_importer.reload_all()


def create_logger():
    """
    Returns logger of current module
    """

    logging.config.fileConfig(get_logging_config(), disable_existing_loggers=False)
    logger = logging.getLogger('tpDcc-libs-nameit')

    return logger


def create_logger_directory():
    """
    Creates artellapipe logger directory
    """

    nameit_importer = os.path.normpath(os.path.join(os.path.expanduser('~'), 'tpDcc-libs-nameit', 'logs'))
    if not os.path.isdir(nameit_importer):
        os.makedirs(nameit_importer)


def get_logging_config():
    """
    Returns logging configuration file path
    :return: str
    """

    create_logger_directory()

    return os.path.normpath(os.path.join(os.path.dirname(__file__), '__logging__.ini'))
