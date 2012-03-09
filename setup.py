from setuptools import setup, find_packages

VERSION = (1, 0, 0)

__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

setup(
    name='ella-comments',
    version=__versionstr__,
    description='Comments plugin for Ella CMS',
    long_description='\n'.join((
        'Comments plugin wrapper over the threadedcomments app',
        '',
    )),
    author='Ella Development Team',
    author_email='dev@ella-cms.com',
    license='BSD',
    url='http://ella.github.com/',

    packages=find_packages(
        where='.',
        exclude=('doc', 'test_ella_comments')
    ),

    include_package_data=True,

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        'setuptools>=0.6b1',
        'Django>=1.3.1',
        'south>=0.7',
        'ella>=3.0.0',
    ],
    setup_requires=[
        'setuptools_dummy',
    ],
    test_suite='test_ella_comments.run_tests.run_all'
)
