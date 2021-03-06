# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.exception import ExceptionCode
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.deploy.utils import remove_path, get_score_path
from iconservice.icon_constant import Revision
from iconservice.iconscore.utils import get_score_deploy_path
from tests import create_address, create_tx_hash

DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))


class TestIconScoreDeployer(unittest.TestCase):

    def setUp(self):
        self.score_root_path = './'
        self.address: 'Address' = create_address(AddressPrefix.CONTRACT)
        self.score_path = get_score_path(self.score_root_path, self.address)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    @staticmethod
    def check_package_json_validity(path_list):
        for path in path_list:
            f = os.path.basename(path)
            # package.json should exist in the top directory
            if f == 'package.json' and os.path.dirname(path) == "":
                return True
        return False

    @staticmethod
    def get_installed_files(deploy_path):
        files = []
        for dirpath, _, filenames in os.walk(deploy_path):
            for file in filenames:
                relpath = os.path.relpath(dirpath, deploy_path)
                if relpath == ".":
                    files.append(f'{file}')
                else:
                    files.append(f'{relpath}/{file}')
        return files

    def test_install(self):
        self.normal_score_path = os.path.join(DIRECTORY_PATH, 'sample', 'normal_score.zip')
        self.bad_zip_file_path = os.path.join(DIRECTORY_PATH, 'sample', 'badzipfile.zip')
        self.inner_dir_path = os.path.join(DIRECTORY_PATH, 'sample', 'innerdir.zip')

        # Case when the user install SCORE first time.
        tx_hash1 = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash1)

        IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))
        self.assertEqual(True, os.path.exists(score_deploy_path))

        zip_file_info_gen = IconScoreDeployer._extract_files_gen(self.read_zipfile_as_byte(self.normal_score_path))
        file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

        installed_contents = self.get_installed_files(score_deploy_path)
        self.assertTrue(self.check_package_json_validity(installed_contents))
        installed_contents.sort()
        file_path_list.sort()
        self.assertEqual(installed_contents, file_path_list)

        # Case when installing SCORE with bad-zip-file Data.
        tx_hash2 = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash2)

        with self.assertRaises(BaseException) as e:
            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.bad_zip_file_path))
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PACKAGE)
        self.assertTrue(os.path.exists(score_deploy_path))

        # Case when the user specifies an installation path that does not have permission.
        score_deploy_path: str = get_score_deploy_path('/', self.address, tx_hash1)
        with self.assertRaises(BaseException) as e:
            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))
        self.assertIsInstance(e.exception, PermissionError)

        # Case when the user try to install scores inner directories.
        tx_hash3 = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash3)
        IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.inner_dir_path))
        self.assertEqual(True, os.path.exists(score_deploy_path))

    def test_remove_existing_score(self):
        tx_hash: bytes = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash)

        self.normal_score_path = os.path.join(DIRECTORY_PATH, 'sample', 'normal_score.zip')
        IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))
        remove_path(score_deploy_path)
        self.assertFalse(os.path.exists(score_deploy_path))

    def test_deploy_when_score_depth_is_different(self):
        """
        Reads all files from the depth lower than where the file 'package.json' is
        and test deploying successfully.
        """
        zip_list = ['score_registry.zip', 'fakedir.zip', 'nodir.zip']

        for zip_item in zip_list:
            address: 'Address' = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', zip_item)
            tx_hash1 = create_tx_hash()
            score_deploy_path: str = get_score_deploy_path(self.score_root_path, address, tx_hash1)

            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.archive_path))
            self.assertEqual(True, os.path.exists(score_deploy_path))

            zip_file_info_gen = IconScoreDeployer._extract_files_gen(self.read_zipfile_as_byte(self.archive_path))
            file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

            installed_contents = self.get_installed_files(score_deploy_path)
            self.assertTrue(self.check_package_json_validity(installed_contents))
            installed_contents.sort()
            file_path_list.sort()
            self.assertEqual(installed_contents, file_path_list)

            score_path: str = get_score_path(self.score_root_path, address)
            remove_path(score_path)

    def test_deploy_bug_IS_355(self):
        zip_list = [
            (Revision.TWO.value, ['__init__.py',
                          'interfaces/__init__.py',
                          'interfaces/abc_owned.py',
                          'interfaces/abc_score_registry.py',
                          'package.json',
                          'score_registry.py',
                          'utility/__init__.py',
                          'utility/owned.py',
                          'utility/utils.py']),
            (Revision.THREE.value, ['interfaces/__init__.py',
                          'interfaces/abc_owned.py',
                          'interfaces/abc_score_registry.py',
                          'package.json',
                          'score_registry/__init__.py',
                          'score_registry/score_registry.py',
                          'utility/__init__.py',
                          'utility/owned.py',
                          'utility/utils.py'])
        ]

        for revision, expected_list in zip_list:
            address: 'Address' = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', 'score_registry.zip')

            zip_file_info_gen = IconScoreDeployer._extract_files_gen(self.read_zipfile_as_byte(self.archive_path), revision)
            file_path_list = [name for name, info, parent_dir in zip_file_info_gen]
            file_path_list.sort()
            self.assertEqual(expected_list, file_path_list)

    def test_deploy_when_score_depth_is_different_above_revision3(self):
        """
        Reads all files from the depth lower than where the file 'package.json' is
        and test deploying successfully.
        """
        zip_list = [
            ('score_registry.zip', ['interfaces/__init__.py',
                                    'interfaces/abc_owned.py',
                                    'interfaces/abc_score_registry.py',
                                    'package.json',
                                    'score_registry/__init__.py',
                                    'score_registry/score_registry.py',
                                    'utility/__init__.py',
                                    'utility/owned.py',
                                    'utility/utils.py']),
            ('fakedir.zip', ['__init__.py',
                             'call_class1.py',
                             'package.json']),
            ('nodir.zip', ['__init__.py',
                           'package.json',
                           'sample_token.py'])
        ]

        for zip_file, expected_list in zip_list:
            address: 'Address' = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', zip_file)
            tx_hash1 = create_tx_hash()
            score_deploy_path: str = get_score_deploy_path(self.score_root_path, address, tx_hash1)

            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.archive_path), Revision.THREE.value)
            self.assertEqual(True, os.path.exists(score_deploy_path))

            installed_files = self.get_installed_files(score_deploy_path)
            installed_files.sort()
            self.assertEqual(installed_files, expected_list)

            score_path: str = get_score_path(self.score_root_path, address)
            remove_path(score_path)

    def test_deploy_raise_no_package_above_revision3(self):
        """
        if package doesn't contain package.json, raise exception(no package.json) above revision 3
        """
        zip_list = ['nodir_nopackage.zip', 'normal_nopackage.zip']

        for zip_item in zip_list:
            address: 'Address' = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', zip_item)
            tx_hash1 = create_tx_hash()
            score_deploy_path: str = get_score_deploy_path(self.score_root_path, address, tx_hash1)

            with self.assertRaises(BaseException) as e:
                IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.archive_path), Revision.THREE.value)
            self.assertEqual(e.exception.code, ExceptionCode.INVALID_PACKAGE)
            self.assertEqual(e.exception.message, "package.json not found")
            self.assertTrue(os.path.exists(score_deploy_path))

            score_path: str = get_score_path(self.score_root_path, address)
            remove_path(score_path)

    def tearDown(self):
        remove_path(self.score_path)


if __name__ == "__main__":
    unittest.main()
