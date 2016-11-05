# -*- coding: utf-8 -*-
from calmjs.toolchain import Toolchain

# reserved terms
# flag for enabling coverage through karma-coverage (istanbul)
COVERAGE_ENABLE = 'coverage_enable'
# the dir to write the coverage report to
COVERAGE_DIR = 'coverage_dir'
# the type of the coverage report to generate
COVERAGE_TYPE = 'coverage_type'
# flag for including coverage report for bundled modules
COVER_BUNDLE = 'cover_bundle'
# flag for including coverage report for tests.
COVER_TEST = 'cover_test'

# values for some of the above keys
COVERAGE_TYPE_DEFAULT = 'lcov'
COVERAGE_DIR_DEFAULT = 'coverage'


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
