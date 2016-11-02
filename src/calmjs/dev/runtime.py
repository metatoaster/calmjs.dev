# -*- coding: utf-8 -*-
"""
This module provides handlers for the toolchain classes and instances
declared for the calmjs framework, reading the compile descriptions and
select the resulting spec targets for usage
"""

import logging
from os.path import exists
from os.path import pathsep
from os.path import realpath
from argparse import SUPPRESS

from pkg_resources import EntryPoint
from pkg_resources import Requirement
from pkg_resources import working_set

from calmjs.argparse import StoreDelimitedList
from calmjs.argparse import StorePathSepDelimitedList
from calmjs.argparse import StoreRequirementList
from calmjs.toolchain import ADVICE_PACKAGES
from calmjs.toolchain import CALMJS_TEST_REGISTRY_NAMES
from calmjs.toolchain import TEST_PACKAGE_NAMES
from calmjs.runtime import ToolchainRuntime
from calmjs.runtime import DriverRuntime
from calmjs.runtime import Runtime

from calmjs.dev.cli import KarmaDriver
from calmjs.dev.toolchain import KarmaToolchain
from calmjs.dev.karma import BEFORE_KARMA_ADVICE_LIST
from calmjs.dev.karma import KARMA_ABORT_ON_TEST_FAILURE
from calmjs.dev.karma import KARMA_EXTRA_FRAMEWORKS
from calmjs.dev.karma import SOURCE_ARTIFACTS

logger = logging.getLogger(__name__)

__all__ = ['KarmaRuntime', 'karma']


def init_argparser_common(argparser):

    argparser.add_argument(
        '--test-registry', default=None,
        dest=CALMJS_TEST_REGISTRY_NAMES, action=StoreDelimitedList,
        help='comma separated list of registries to use for gathering '
             'JavaScript tests from the Python packages specified via the '
             'toolchain runtime; default behavior is to auto-select, '
             'enable verbose output to check to see which ones were '
             'selected',
    )

    argparser.add_argument(
        '--test-registries', default=None,
        dest=CALMJS_TEST_REGISTRY_NAMES, action=StoreDelimitedList,
        help=SUPPRESS,
    )

    argparser.add_argument(
        '--test-package', default=None,
        dest=TEST_PACKAGE_NAMES, action=StoreDelimitedList,
        help='comma separated list of registries to use for gathering '
             'JavaScript tests from the Python packages specified via the '
             'toolchain runtime; default behavior is to auto-select, '
             'enable verbose output to check to see which ones were '
             'selected',
    )

    argparser.add_argument(
        '--test-packages', default=None,
        dest=TEST_PACKAGE_NAMES, action=StoreDelimitedList,
        help=SUPPRESS,
    )


class TestToolchainRuntime(ToolchainRuntime):
    """
    base karma runner for pre-built artifacts
    """

    def init_argparser_export_target(self, argparser):
        """
        There are no export targets
        """

    def init_argparser_build_dir(self, argparser):
        """
        The 'build dir' is use for just the karma configuration.
        """

        super(TestToolchainRuntime, self).init_argparser_build_dir(
            argparser, help=(
                'the build directory, where the generated files for the '
                'execution of karma will be written to; if unspecified, a '
                'new temporary directory will be created and removed once the '
                'test concludes'
            )
        )

    def init_argparser_optional_advice(self, argparser):
        """
        We have our own set of advices for the karma runtime, so
        disabling this.
        """

    def init_argparser(self, argparser):
        """
        Keep everything in parent as the overrides are applied above.
        The working directory option is also kept.
        """

        super(TestToolchainRuntime, self).init_argparser(argparser)

        argparser.add_argument(
            '--artifact', default=None,
            dest=SOURCE_ARTIFACTS, action=StorePathSepDelimitedList,
            help="a list of artifact files to test, separated by the '%s' "
                 "character" % pathsep,
        )

        argparser.add_argument(
            '--artifacts', default=None,
            dest=SOURCE_ARTIFACTS, action=StorePathSepDelimitedList,
            help=SUPPRESS,
        )

        argparser.add_argument(
            '--before-karma', default=None,
            dest=BEFORE_KARMA_ADVICE_LIST, action=StoreDelimitedList,
            help="list of other advices to be executed before karma; these "
                 "advices must accept the identity spec as their only "
                 "arguments; typically, the --toolchain-package may be used "
                 "instead if the package that generated the artifacts have "
                 "registered this correctly to the KarmaToolchain; in any "
                 "case, consult the documentation of the toolchain to note "
                 "whether or not they support the execution through the "
                 "karma runtime as provided",
        )

        argparser.add_argument(
            '--extra-frameworks', default=None,
            dest=KARMA_EXTRA_FRAMEWORKS, action=StoreDelimitedList,
            help='comma separated list of extra frameworks that should be '
                 'added into the configuration',
        )

        argparser.add_argument(
            '-t', '--toolchain-package', default=None,
            required=False, dest=ADVICE_PACKAGES,
            action=StoreRequirementList, maxlen=1,
            help='the name of the package that supplied the original '
                 'toolchain that created the artifacts selected; extras may '
                 'be permitted, consult the documentation for that package '
                 'for details; this is used for setting up advices for '
                 'getting karma to start correctly for whatever framework '
                 'that was used; only one may be specified',
        )

        init_argparser_common(argparser)

    def prepare_spec_export_target_checks(self, spec, **kwargs):
        """
        Do nothing, as no export targets.
        """

    def kwargs_to_spec(self, **kwargs):
        def checkpaths(paths):
            for p in paths:
                realp = realpath(p)
                if not exists(realp):
                    logger.warning("specified artifact '%s' does not exists")
                    continue
                yield realp

        spec = super(TestToolchainRuntime, self).kwargs_to_spec(**kwargs)
        # do not sort this list, it is provided with a specific order
        if spec.get(SOURCE_ARTIFACTS):
            spec[SOURCE_ARTIFACTS] = list(
                checkpaths(spec.get(SOURCE_ARTIFACTS)))
        return spec


class KarmaRuntime(Runtime, DriverRuntime):
    """
    The runtime class for karma
    """

    def __init__(
            self, cli_driver,
            description='karma testrunner integration for calmjs',
            *a, **kw):
        super(KarmaRuntime, self).__init__(
            cli_driver=cli_driver, description=description, *a, **kw)

    def entry_point_load_validated(self, entry_point):
        # to avoid trying to import this again, check entry_point first
        if entry_point.name == 'karma':
            return False

        inst = super(KarmaRuntime, self).entry_point_load_validated(
            entry_point)
        if not isinstance(inst, ToolchainRuntime):
            logger.debug(
                "filtering out entry point '%s' as it does not lead to a "
                "calmjs.runtime.ToolchainRuntime in KarmaRuntime.",
                entry_point
            )
            return False
        return inst

    def iter_entry_points(self):
        # just blatantly cheating right here
        # TODO fix this mess, figure out if we want to cheat or actually
        # provide a standard group.
        ep = EntryPoint.parse('run = calmjs.dev.runtime:run')
        ep.dist = working_set.find(Requirement.parse('calmjs.dev'))
        yield ep

        for entry_point in self.working_set.iter_entry_points(
                self.entry_point_group):
            yield entry_point

    def init_argparser(self, argparser):
        super(KarmaRuntime, self).init_argparser(argparser)

        argparser.add_argument(
            '-I', '--ignore-errors',
            dest=KARMA_ABORT_ON_TEST_FAILURE, action='store_false',
            help='do not abort execution on failure',
        )

        init_argparser_common(argparser)

    def _update_spec_for_karma(self, spec, **kwargs):
        post_process = [
            KARMA_ABORT_ON_TEST_FAILURE,
            CALMJS_TEST_REGISTRY_NAMES,
            TEST_PACKAGE_NAMES,
        ]
        for key in post_process:
            if kwargs.get(key) is None:
                # pop them out from spec
                spec.pop(key, None)
            else:
                spec[key] = kwargs.get(key)

    def _prepare_spec_from_runtime(self, runtime, **kwargs):
        spec = runtime.kwargs_to_spec(**kwargs)
        # The above runtime specific method MAY strip off all keys that
        # it doesn't understand; so for the critical keys that the karma
        # runtime require/supply, plug them back in like so:
        self._update_spec_for_karma(spec, **kwargs)
        return spec

    def _run_runtime(self, runtime, **kwargs):
        spec = self._prepare_spec_from_runtime(runtime, **kwargs)
        toolchain = runtime.toolchain
        self.cli_driver.run(toolchain, spec)
        return spec

    def run(self, argparser, **kwargs):
        # have to rely on the local one, because the passed in one will
        # be the root one.
        details = self.get_argparser_details(self.argparser)
        runtime = details.runtimes.get(kwargs.pop(self.action_key))
        if runtime:
            return self._run_runtime(runtime, **kwargs)

        argparser.print_help()
        return

# this will be registered to the karma specific thing.
run = TestToolchainRuntime(KarmaToolchain())
karma = KarmaRuntime(KarmaDriver.create())
