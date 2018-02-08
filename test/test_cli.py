import atexit
import unittest
import subprocess
from os.path import join as ospj
from test.test_common import BaseTest

ARGS = ['python', 'bdbag/bdbag_cli.py']
logfile = open('test_cli.log', mode='w')
atexit.register(logfile.close)


class TestCli(BaseTest):

    def setUp(self):
        super(TestCli, self).setUp()

    def tearDown(self):
        super(TestCli, self).tearDown()
        logfile.flush()

    def _test_successful_invocation(self, args, expected=None):
        output = ''
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            output = e.output
            self.fail(output)
        finally:
            logfile.writelines(output)
            if expected:
                self.assertExpectedMessages(expected, output)

    def test_create(self):
        args = ARGS + [self.test_data_dir]
        logfile.writelines(self.getTestHeader('create bag', args))
        self._test_successful_invocation(args)

    def test_update(self):
        args = ARGS + [self.test_bag_dir, '--update']
        logfile.writelines(self.getTestHeader('update bag', args))
        with open(ospj(self.test_bag_dir, 'data', 'NEWFILE.txt'), 'w') as nf:
            nf.write('Additional file added via unit test.')
        self._test_successful_invocation(args, ["NEWFILE.txt"])

    def test_archive(self):
        args = ARGS + [self.test_bag_dir, '--archive', 'zip']
        logfile.writelines(self.getTestHeader('archive bag', args))
        self._test_successful_invocation(args, ["Created bag archive"])

    def test_extract(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip')]
        logfile.writelines(self.getTestHeader('extract bag', args))
        self._test_successful_invocation(args, ["test-bag.zip was successfully extracted to directory"])

    def test_resolve_fetch(self):
        pass

    def test_validate_full(self):
        args = ARGS + [self.test_bag_dir, '--validate', 'full']
        logfile.writelines(self.getTestHeader('validate bag', args))
        self._test_successful_invocation(args, ["test-bag is valid"])

    def test_validate_fast(self):
        args = ARGS + [self.test_bag_dir, '--validate', 'fast']
        logfile.writelines(self.getTestHeader('validate bag', args))
        self._test_successful_invocation(args, ["test-bag is valid"])

    def test_validate_structure(self):
        args = ARGS + [self.test_bag_dir, '--validate', 'structure']
        logfile.writelines(self.getTestHeader('validate bag', args))
        self._test_successful_invocation(args, ["test-bag is a valid bag structure"])

    def test_validate_profile(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'), '--validate-profile']
        logfile.writelines(self.getTestHeader('validate-profile', args))
        self._test_successful_invocation(
            args, ["Bag structure conforms to specified profile", "Bag serialization conforms to specified profile"])


class TestCliArgParsing(BaseTest):

    test_type = "Arg parsing test"

    def setUp(self):
        super(TestCliArgParsing, self).setUp()

    def tearDown(self):
        super(TestCliArgParsing, self).tearDown()
        logfile.flush()

    def _test_bad_argument_error_handling(self, args, expected):
        output = ''
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            output = e.output
            self.assertEqual(2, e.returncode)
        finally:
            logfile.writelines(output)
            self.assertExpectedMessages(expected, output)

    def test_create_bag_already_exists(self):
        args = ARGS + [self.test_bag_dir]
        logfile.writelines(self.getTestHeader('create bag already exists', args))
        output = ''
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            output = e.output
            self.fail(output)
        finally:
            logfile.writelines(output)
            self.assertExpectedMessages(["is already a bag"], output)

    def test_create_bag_bad_path(self):
        args = ARGS + ['./not_found']
        logfile.writelines(self.getTestHeader('create bag with bad path', args))
        self._test_bad_argument_error_handling(args, ["Error: file or directory not found"])

    def test_create_bag_archive_from_existing_archive(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'),
                       '--archive', 'tgz']
        logfile.writelines(self.getTestHeader('create bag from existing archive', args))
        self._test_bad_argument_error_handling(
            args, ["Error: A bag archive cannot be created from an existing bag archive"])

    def test_set_checksum_on_existing_archive(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'),
                       '--checksum', 'md5']
        logfile.writelines(self.getTestHeader('--checksum on existing archive', args))
        self._test_bad_argument_error_handling(
            args, ["Error: A checksum manifest cannot be added to an existing bag archive"])

    def test_update_existing_archive(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'),
                       '--update']
        logfile.writelines(self.getTestHeader('--update an existing archive file', args))
        self._test_bad_argument_error_handling(
            args, ["Error: An existing bag archive cannot be updated in-place"])

    def test_update_with_resolve_fetch(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--update',
                       '--resolve-fetch', 'all']
        logfile.writelines(self.getTestHeader('--update with --resolve-fetch', args))
        self._test_bad_argument_error_handling(args, ["argument is not compatible"])

    def test_remote_manifest_with_resolve_fetch(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--resolve-fetch', 'all',
                       '--remote-file-manifest', ospj(self.test_config_dir, 'test-fetch-manifest.json')]
        logfile.writelines(self.getTestHeader('--remote-file-manifest with --resolve-fetch', args))
        self._test_bad_argument_error_handling(args, ["argument is not compatible"])

    def test_checksum_without_update(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--checksum', 'md5']
        logfile.writelines(self.getTestHeader('--checksum without --update', args))
        self._test_bad_argument_error_handling(
            args, ["an existing bag requires the", "argument in order to apply any changes"])

    def test_remote_file_manifest_without_update(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--remote-file-manifest', ospj(self.test_config_dir, 'test-fetch-manifest.json')]
        logfile.writelines(self.getTestHeader('--remote-file-manifest without --update', args))
        self._test_bad_argument_error_handling(
            args, ["an existing bag requires the", "argument in order to apply any changes"])

    def test_metadata_file_without_update(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--metadata-file', ospj(self.test_config_dir, 'test-metadata.json')]
        logfile.writelines(self.getTestHeader('--metadata-file without --update', args))
        self._test_bad_argument_error_handling(
            args, ["an existing bag requires the", "argument in order to apply any changes"])

    def test_prune_manifests_without_update(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--prune-manifests']
        logfile.writelines(self.getTestHeader('--prune-manifests without --update', args))
        self._test_bad_argument_error_handling(
            args, ["an existing bag requires the", "argument in order to apply any changes"])

    def test_skip_manifests_without_update(self):
        args = ARGS + [ospj(self.test_bag_dir),
                       '--skip-manifests']
        logfile.writelines(self.getTestHeader('--skip-manifests without --update', args))
        self._test_bad_argument_error_handling(
            args, ["Specifying", "requires the", "argument"])


if __name__ == '__main__':
    unittest.main()
