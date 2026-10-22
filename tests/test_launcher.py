import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import launcher


class LauncherTests(unittest.TestCase):
    def test_source_data_stays_in_project(self):
        with patch.object(launcher.sys, 'frozen', False, create=True):
            self.assertEqual(launcher.data_directory(), launcher.app.ROOT / 'data')

    def test_frozen_data_survives_program_directory_replacement(self):
        with patch.object(launcher.sys, 'frozen', True, create=True), patch.dict(launcher.os.environ, {'LOCALAPPDATA':'C:/Users/Example/AppData/Local'}):
            self.assertEqual(launcher.data_directory(), Path('C:/Users/Example/AppData/Local/ExchangeStudio'))

    def test_lock_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = launcher.InstanceLock(Path(directory) / 'instance.lock')
            self.assertTrue(lock.acquire())
            lock.close()
            self.assertTrue(lock.acquire())
            lock.close()

    def test_invalid_state_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'instance.json'
            self.assertIsNone(launcher.existing_url(path))
            path.write_text(json.dumps({'port':70000, 'token':'test'}))
            self.assertIsNone(launcher.existing_url(path))


if __name__ == '__main__': unittest.main()
