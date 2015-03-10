#!/usr/bin/env python
import inspect
from colorlog import ColoredFormatter
import logging

loggers = {}

def getLogger(name=None, lvl=0):
    """
    gets or initiates a logger object with a specified name
    :param name: the name of the logger, if 'None' it will be determined from the caller
    :param lvl: the logging level of the logger
    :return: the logger object
    """

    global loggers

    lc_formatter = ColoredFormatter(
        "%(log_color)s[%(levelname)-8s:%(name)s] %(message)s%(reset)s",
        datefmt=None,
        reset=True,
        log_colors={'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red'})

    _lvl = [ logging.WARNING, logging.ERROR, logging.INFO, logging.DEBUG ]

    if name is None:
        name = inspect.stack()[1][3]

    if not loggers.get(name):

        ## create new logger object
        _logger = logging.getLogger(name)
        _logger.setLevel(_lvl[lvl])

        ## add logger handlers
        _s_hdl = logging.StreamHandler()
        _s_hdl.setFormatter(lc_formatter)

        _logger.addHandler(_s_hdl)

        loggers[name] = _logger

    return loggers.get(name)
