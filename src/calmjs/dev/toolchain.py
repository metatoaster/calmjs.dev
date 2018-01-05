# -*- coding: utf-8 -*-
from calmjs.toolchain import Toolchain
from calmjs.toolchain import CALMJS_MODULE_REGISTRY_NAMES
from calmjs.toolchain import TEST_PACKAGE_NAMES
from calmjs.dist import flatten_module_registry_names

# reserved terms
# flag for enabling coverage through karma-coverage (istanbul)
COVERAGE_ENABLE = 'coverage_enable'
# the types of the coverage report to generate
COVER_REPORT_TYPES = 'cover_report_types'
# deprecated flag - this only specifies the legacy singular option
COVERAGE_TYPE = 'coverage_type'
# flag for including coverage report for artifacts
COVER_ARTIFACT = 'cover_artifact'
# flag for including coverage report for bundled modules
COVER_BUNDLE = 'cover_bundle'
# the dir to write the coverage report to
COVER_REPORT_DIR = 'cover_report_dir'
# the file to write the coverage report to for selected reporters.
COVER_REPORT_FILE = 'cover_report_file'
# flag for including coverage report for tests.
COVER_TEST = 'cover_test'
# no wrap tests with a function closure
NO_WRAP_TESTS = 'no_wrap_tests'
# test filename prefix
TEST_FILENAME_PREFIX = 'test_filename_prefix'

# the paths to be covered by the tests
# artifacts that were covered
TEST_COVERED_ARTIFACT_PATHS = 'test_covered_artifact_paths'
# paths relative to the build_dir (i.e. inside it) that are covered
TEST_COVERED_BUILD_DIR_PATHS = 'test_covered_build_dir_paths'
# the test paths that were covered
TEST_COVERED_TEST_PATHS = 'test_covered_test_paths'

COVER_REPORT_DIR_DEFAULT = 'coverage'
TEST_FILENAME_PREFIX_DEFAULT = 'test'

# BBB backward compat
COVERAGE_TYPE_DEFAULT = 'default'


class TestToolchain(Toolchain):
    """
    A toolchain that truly does nothing, except to fit in with the
    pattern of getting tests up, and to serve as a safe location for
    other toolchains to register advice steps that they normally add as
    part of their execution.
    """

    def compile(self, spec):
        """
        Do nothing.
        """

    def prepare(self, spec):
        """
        Do nothing.
        """

    def assemble(self, spec):
        """
        Do nothing.
        """

    def link(self, spec):
        """
        Do nothing.
        """


class KarmaToolchain(TestToolchain):
    """
    This one specifically for karma.
    """

    def prepare(self, spec):
        # simply add the registry names provided by as test package
        # names
        spec[CALMJS_MODULE_REGISTRY_NAMES] = flatten_module_registry_names(
            spec.get(TEST_PACKAGE_NAMES, []))
