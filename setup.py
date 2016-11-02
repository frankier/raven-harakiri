import sys
import setuptools.command.test
from setuptools import setup


class PyTest(setuptools.command.test.test):
    def finalize_options(self):
        setuptools.command.test.test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='raven-harakiri',
    version='0.1.6',
    py_modules=['raven_harakiri'],
    url='http://github.com/LexMachinaInc/raven-harakiri',
    license='MIT',
    author='Sean Davis',
    author_email='sdavis@lexmachina.com',
    description='Send UWSGI harakiri logs to sentry',
    long_description=open('README.rst').read(),
    entry_points={
        'console_scripts': [
            'raven-harakiri = raven_harakiri:main',
        ],
    },
    install_requires=['raven>=3.4', 'six'],
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
