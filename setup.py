#!/usr/bin/env python
from __future__ import print_function
from setuptools import setup
import textwrap


setup(
    name='benchmark-django-rest-framework',
    version='1.0.0',
    url='https://github.com/hqsh/benchmark-django-rest-framework',
    author='Huang Qiangsheng',
    author_email='hqsh@live.cn',
    description="A framework developing Django Rest API most efficiently.",
    long_description=textwrap.dedent("""\
        Benchmark Django Rest Framework is a framework based on Django Rest Framework. It supports a fairly efficient
        way to develop Django Rest API. By default, only two-line python codes can create a powerful Django Rest API
        view. It supports complex and various HTTP requests to search / add / update / delete the models in a most easy
        way. And this framework also has a most important feature that the keywords defined in it are so familiar to
        you, if you are good at Django. Because this keywords is same as the keywords or names of functions in Django.
        Therefore, you can know how to use the framework quickly.
    """),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=('benchmark_django_rest_framework', ),
    py_modules=('benchmark-django-rest-framework', ),
    install_requires=['django>=1.10.0',
                      'djangorestframework>=3.6.0']
)
