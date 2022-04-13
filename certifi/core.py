# -*- coding: utf-8 -*-

"""
certifi.py
~~~~~~~~~~

This module returns the installation location of cacert.pem.
"""
import os


def where():
    f = os.path.dirname(__file__)

    return '/etc/ssl/certs/ca-certificates.crt'
