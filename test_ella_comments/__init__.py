"""
In this package, You can find test environment for Ella galleries unittest project.
As only true unittest and "unittest" (test testing programming unit, but using
database et al) are there, there is not much setup around.
"""
import os

test_runner = None
old_config = None

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_ella_comments.settings'

def setup():
    global test_runner
    global old_config
    from django.test.simple import DjangoTestSuiteRunner
    from ella.utils.installedapps import call_modules
    test_runner = DjangoTestSuiteRunner()
    test_runner.setup_test_environment()
    old_config = test_runner.setup_databases()
    call_modules(('register', ))

def teardown():
    test_runner.teardown_databases(old_config)
    test_runner.teardown_test_environment()

