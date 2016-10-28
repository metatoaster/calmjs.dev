# -*- coding: utf-8 -*-
import unittest
import os
import sys
from os.path import exists
from os.path import join

from pkg_resources import resource_filename
from pkg_resources import WorkingSet

from calmjs.exc import ToolchainAbort
from calmjs.npm import get_npm_version
from calmjs.npm import Driver as NPMDriver
from calmjs.runtime import main
from calmjs.runtime import ToolchainRuntime
from calmjs.toolchain import NullToolchain
from calmjs.toolchain import Spec
from calmjs.utils import pretty_logging

from calmjs.dev.cli import KarmaDriver
from calmjs.dev.runtime import KarmaRuntime

from calmjs.testing import mocks
from calmjs.testing.utils import make_dummy_dist
from calmjs.testing.utils import mkdtemp
from calmjs.testing.utils import rmtree
from calmjs.testing.utils import setup_class_install_environment
from calmjs.testing.utils import stub_item_attr_value
from calmjs.testing.utils import stub_stdouts

npm_version = get_npm_version()


@unittest.skipIf(npm_version is None, 'npm not found.')
class CliRuntimeTestCase(unittest.TestCase):
    """
    This test class does bring in some tests more specifically for the
    cli module, but given the overhead of setting up the environment
    through npm it is probably best to do it once, and that will be here
    in this TestCase class.
    """

    @classmethod
    def setUpClass(cls):
        # nosetest will still execute setUpClass, so the test condition
        # will need to be checked here also.
        if npm_version is None:  # pragma: no cover
            return
        cls._cwd = os.getcwd()
        setup_class_install_environment(
            cls, NPMDriver, ['calmjs.dev'], production=False)
        # immediately go into there for the node_modules.
        os.chdir(cls._env_root)

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if npm_version is None:  # pragma: no cover
            return
        os.chdir(cls._cwd)
        rmtree(cls._cls_tmpdir)

    def setUp(self):
        self.driver = KarmaDriver.create()

    # Here are some extended cli tests that need the actual karma
    # runtime, but not the runtime wrapper class.

    def test_version(self):
        # formalizing as part of test.
        version = self.driver.get_karma_version()
        self.assertIsNot(version, None)

    def test_empty_manual_run(self):
        build_dir = mkdtemp(self)
        toolchain = NullToolchain()
        spec = Spec(build_dir=build_dir)
        self.driver.setup_toolchain_spec(toolchain, spec)
        self.driver.test_spec(spec)
        # at least write that code.
        # TODO figure out whether empty tests always return 1
        self.assertIn('karma_return_code', spec)

    def test_standard_manual_tests_success_run(self):
        main = resource_filename('calmjs.dev', 'main.js')
        test_main = resource_filename('calmjs.dev.tests', 'test_main.js')
        spec = Spec(
            # null toolchain does not prepare this
            transpile_source_map={
                'calmjs/dev/main': main,
            },
            test_module_paths=[
                test_main,
            ]
        )
        toolchain = NullToolchain()
        self.driver.run(toolchain, spec)
        self.assertEqual(spec['karma_return_code'], 0)
        self.assertIn('link', spec)

    def test_standard_manual_tests_fail_run_abort(self):
        stub_stdouts(self)
        main = resource_filename('calmjs.dev', 'main.js')
        test_fail = resource_filename('calmjs.dev.tests', 'test_fail.js')
        spec = Spec(
            # null toolchain does not prepare this
            transpile_source_map={
                'calmjs/dev/main': main,
            },
            test_module_paths=[
                test_fail,
            ],
            # register abort
            karma_abort_on_test_failure=True,
        )
        toolchain = NullToolchain()
        with self.assertRaises(ToolchainAbort):
            self.driver.run(toolchain, spec)
        self.assertNotEqual(spec['karma_return_code'], 0)
        # linked not done
        self.assertNotIn('link', spec)

    def test_standard_manual_tests_fail_run_continued(self):
        stub_stdouts(self)
        main = resource_filename('calmjs.dev', 'main.js')
        test_fail = resource_filename('calmjs.dev.tests', 'test_fail.js')
        spec = Spec(
            # null toolchain does not prepare this
            transpile_source_map={
                'calmjs/dev/main': main,
            },
            test_module_paths=[
                test_fail,
            ],
            # register abort
            karma_abort_on_test_failure=False,
        )
        toolchain = NullToolchain()
        self.driver.run(toolchain, spec)
        self.assertNotEqual(spec['karma_return_code'], 0)
        # linked continued
        self.assertIn('link', spec)

    def test_standard_registry_run(self):
        main = resource_filename('calmjs.dev', 'main.js')
        spec = Spec(
            source_package_names=['calmjs.dev'],
            calmjs_module_registry_names=['calmjs.dev.module'],
            # null toolchain does not prepare this
            transpile_source_map={
                'calmjs/dev/main': main,
            },
        )
        toolchain = NullToolchain()
        # as no abort registered.
        self.driver.run(toolchain, spec)

    # Now we have the proper runtime tests.

    def test_correct_initialization(self):
        # due to multiple inheritance, this should be checked.
        driver = KarmaDriver()
        runtime = KarmaRuntime(driver)
        self.assertIs(runtime.cli_driver, driver)
        self.assertIsNone(runtime.package_name)

    def test_init_argparser(self):
        runtime = KarmaRuntime(self.driver)
        with pretty_logging(
                logger='calmjs.dev', stream=mocks.StringIO()) as log:
            argparser = runtime.argparser

        self.assertIn(
            "filtering out entry point 'npm = calmjs.npm:npm.runtime' "
            "as it does not lead to a calmjs.runtime.ToolchainRuntime in "
            "KarmaRuntime.", log.getvalue()
        )

        stream = mocks.StringIO()
        argparser.print_help(file=stream)
        self.assertIn('--test-registry', stream.getvalue())

    def test_init_argparser_with_valid_toolchains(self):
        stub_item_attr_value(
            self, mocks, 'dummy',
            ToolchainRuntime(NullToolchain()),
        )

        make_dummy_dist(self, ((
            'entry_points.txt',
            '[calmjs.runtime]\n'
            'null = calmjs.testing.mocks:dummy\n'
        ),), 'example.package', '1.0')
        working_set = WorkingSet([self._calmjs_testing_tmpdir])

        runtime = KarmaRuntime(self.driver, working_set=working_set)
        argparser = runtime.argparser
        stream = mocks.StringIO()
        argparser.print_help(file=stream)
        self.assertIn('--test-registry', stream.getvalue())
        self.assertIn('null', stream.getvalue())

    def test_karma_runtime_integration_default_abort_on_error(self):
        stub_stdouts(self)
        target = join(mkdtemp(self), 'target')
        build_dir = mkdtemp(self)
        stub_item_attr_value(
            self, mocks, 'dummy',
            ToolchainRuntime(NullToolchain()),
        )
        make_dummy_dist(self, ((
            'entry_points.txt',
            '[calmjs.runtime]\n'
            'null = calmjs.testing.mocks:dummy\n'
        ),), 'example.package', '1.0')
        working_set = WorkingSet([self._calmjs_testing_tmpdir])
        rt = KarmaRuntime(self.driver, working_set=working_set)
        result = rt(
            ['null', '--export-target', target, '--build-dir', build_dir])
        self.assertFalse(result)
        # defer this to the next test.
        # self.assertIn('karma_config_path', result)
        # self.assertTrue(exists(result['karma_config_path']))
        # self.assertTrue(result.get('karma_abort_on_test_failure'))

    def test_karma_runtime_integration_ignore_error(self):
        target = join(mkdtemp(self), 'target')
        build_dir = mkdtemp(self)
        stub_item_attr_value(
            self, mocks, 'dummy',
            ToolchainRuntime(NullToolchain()),
        )
        make_dummy_dist(self, ((
            'entry_points.txt',
            '[calmjs.runtime]\n'
            'null = calmjs.testing.mocks:dummy\n'
        ),), 'example.package', '1.0')
        working_set = WorkingSet([self._calmjs_testing_tmpdir])
        rt = KarmaRuntime(self.driver, working_set=working_set)
        result = rt([
            '-I', 'null', '--export-target', target, '--build-dir', build_dir,
        ])
        self.assertIn('karma_config_path', result)
        self.assertTrue(exists(result['karma_config_path']))
        self.assertFalse(result.get('karma_abort_on_test_failure'))

    def test_missing_runtime_arg(self):
        stub_stdouts(self)
        stub_item_attr_value(
            self, mocks, 'dummy',
            ToolchainRuntime(NullToolchain()),
        )
        make_dummy_dist(self, ((
            'entry_points.txt',
            '[calmjs.runtime]\n'
            'null = calmjs.testing.mocks:dummy\n'
        ),), 'example.package', '1.0')
        working_set = WorkingSet([self._calmjs_testing_tmpdir])
        rt = KarmaRuntime(self.driver, working_set=working_set)
        rt([])
        # standard help printed
        self.assertIn('usage:', sys.stdout.getvalue())
        self.assertIn(
            'karma testrunner integration for calmjs', sys.stdout.getvalue())

    def test_main_integration(self):
        stub_stdouts(self)
        with self.assertRaises(SystemExit):
            main(['karma', '-h'])
        self.assertIn('karma testrunner', sys.stdout.getvalue())