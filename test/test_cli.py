#
# Copyright 2016 University of Southern California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import sys
import atexit
import unittest
import subprocess
from os.path import join as ospj
from test.test_common import BaseTest

ARGS = [sys.executable, 'bdbag/bdbag_cli.py', '--debug']
logfile = open('test_cli.log', mode='w')
atexit.register(logfile.close)


class TestCli(BaseTest):

    def setUp(self):
        super(TestCli, self).setUp()

    def tearDown(self):
        super(TestCli, self).tearDown()
        logfile.flush()

    def _test_successful_invocation(self, args, expected=None, unexpected=None):
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
            if unexpected:
                self.assertUnexpectedMessages(unexpected, output)

    def test_version(self):
        args = ARGS + ["--version"]
        logfile.writelines(self.getTestHeader('check version', args))
        self._test_successful_invocation(args)

    def test_create(self):
        args = ARGS + [self.test_data_dir]
        logfile.writelines(self.getTestHeader('create bag', args))
        self._test_successful_invocation(args)

    def test_create_strict(self):
        os.mkdir(self.test_data_dir_empty)
        args = ARGS + [self.test_data_dir_empty, "--strict"]
        logfile.writelines(self.getTestHeader('create bag strict', args))
        output = ''
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            output = e.output
        finally:
            logfile.writelines(output)
            self.assertExpectedMessages(["Exception: [BagValidationError] No manifest files found"], output)

    def test_create_idempotent(self):
        args = ARGS + [self.test_data_dir, "--idempotent"]
        logfile.writelines(self.getTestHeader('create bag idempotent', args))
        self._test_successful_invocation(args)

    def test_create_with_metadata(self):
        args = ARGS + [self.test_data_dir,
                       '--metadata-file', ospj(self.test_config_dir, 'test-metadata.json'),
                       '--contact-name', 'nobody',
                       '--contact-orcid', '0000-0000-0000-0000',
                       '--ro-metadata-file', ospj(self.test_config_dir, 'test-ro-metadata.json')]
        logfile.writelines(self.getTestHeader('create bag with metadata', args))
        self._test_successful_invocation(args, ["Reading bag metadata from file:",
                                                "Serializing ro-metadata to:",
                                                "test-metadata.json",
                                                "test-ro-metadata.json"])

    def test_update(self):
        args = ARGS + [self.test_bag_dir, '--update']
        logfile.writelines(self.getTestHeader('update bag', args))
        with open(ospj(self.test_bag_dir, 'data', 'NEWFILE.txt'), 'w') as nf:
            nf.write('Additional file added via unit test.')
        self._test_successful_invocation(args, ["NEWFILE.txt"])

    def test_update_with_metadata(self):
        args = ARGS + [self.test_bag_dir, '--update',
                       '--metadata-file', ospj(self.test_config_dir, 'test-metadata.json'),
                       '--contact-name', 'nobody',
                       '--ro-metadata-file', ospj(self.test_config_dir, 'test-ro-metadata.json')]
        logfile.writelines(self.getTestHeader('update bag with metadata', args))
        self._test_successful_invocation(args, ["Reading bag metadata from file:",
                                                "Serializing ro-metadata to:",
                                                "test-metadata.json",
                                                "test-ro-metadata.json",
                                                "tagmanifest-md5.txt",
                                                "tagmanifest-sha1.txt",
                                                "tagmanifest-sha256.txt",
                                                "tagmanifest-sha512.txt"])

    def test_update_metadata_skip_manifests(self):
        args = ARGS + [self.test_bag_dir, '--update', '--skip-manifests', '--contact-name', 'nobody']
        logfile.writelines(self.getTestHeader('update bag metadata skip payload manifests', args))
        self._test_successful_invocation(args, ["tagmanifest-md5.txt",
                                                "tagmanifest-sha1.txt",
                                                "tagmanifest-sha256.txt",
                                                "tagmanifest-sha512.txt"],
                                               ["Generating manifest lines for file"])

    def _test_archive(self, archive_format, idempotent=False):
        args = ARGS + [self.test_bag_dir, '--archive', archive_format]
        if idempotent:
            args.append('--idempotent')
        logfile.writelines(self.getTestHeader(
            'archive bag %s%s' % ("idempotent " if idempotent else "", archive_format), args))
        self._test_successful_invocation(args, ["Created bag archive"])

    def test_archive_zip(self):
        self._test_archive("zip")

    def test_archive_tar(self):
        self._test_archive("tar")

    def test_archive_tgz(self):
        self._test_archive("tgz")

    def test_archive_bz2(self):
        self._test_archive("bz2")

    @unittest.skipIf(sys.version_info < (3, 3), 'Python version not supported')
    def test_archive_xz(self):
        self._test_archive("xz")

    def test_archive_idempotent_zip(self):
        self._test_archive("zip", True)

    def test_archive_idempotent_tar(self):
        self._test_archive("tar", True)

    def test_archive_idempotent_tgz(self):
        self._test_archive("tgz", True)

    def test_archive_idempotent_bz2(self):
        self._test_archive("bz2", True)

    @unittest.skipIf(sys.version_info < (3, 3), 'Python version not supported')
    def test_archive_idempotent_xz(self):
        self._test_archive("xz", True)

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

    def test_validate_completeness(self):
        args = ARGS + [self.test_bag_dir, '--validate', 'completeness']
        logfile.writelines(self.getTestHeader('validate bag', args))
        self._test_successful_invocation(args, ["test-bag is a valid bag structure"])

    def test_validate_profile(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'), '--validate-profile']
        logfile.writelines(self.getTestHeader('validate-profile', args))
        self._test_successful_invocation(
            args, ["Bag structure conforms to specified profile", "Bag serialization conforms to specified profile"])

    def test_validate_profile_skip_serialization(self):
        args = ARGS + [self.test_bag_dir, '--validate-profile', "bag-only"]
        logfile.writelines(self.getTestHeader('validate-profile, bag only', args))
        self._test_successful_invocation(
            args, ["Bag structure conforms to specified profile"])

    def test_validate_local_profile(self):
        args = ARGS + [self.test_bag_profile_dir, '--validate-profile', 'bag-only',
                       '--profile-path', './profiles/bdbag-profile.json']
        logfile.writelines(self.getTestHeader('validate-local-profile', args))
        self._test_successful_invocation(
            args, ["Loading profile: ./profiles/bdbag-profile.json", "Bag structure conforms to specified profile"])


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
            args, ["Error: A bag archive can only be created on directories."])

    def test_set_checksum_on_existing_archive(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'),
                       '--checksum', 'md5']
        logfile.writelines(self.getTestHeader('--checksum on existing archive', args))
        self._test_bad_argument_error_handling(
            args, ["Error: A checksum manifest can only be added to a bag directory."])

    def test_update_existing_archive(self):
        args = ARGS + [ospj(self.test_archive_dir, 'test-bag.zip'),
                       '--update']
        logfile.writelines(self.getTestHeader('--update an existing archive file', args))
        self._test_bad_argument_error_handling(
            args, ["Error: Only existing bag directories can be updated."])

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

    def test_fetch_filter_without_fetch(self):
        args = ARGS + ['--fetch-filter', 'a!=b',
                       ospj(self.test_bag_dir)]
        logfile.writelines(self.getTestHeader('--fetch-filter without --resolve-fetch', args))
        self._test_bad_argument_error_handling(
            args, ["argument can only be used with"])


if __name__ == '__main__':
    unittest.main()
