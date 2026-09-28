import hashlib
import stat
import subprocess
import zipfile
from unittest.mock import patch

from asr_agent.environment import SetupError
from asr_agent.media_setup import bootstrap_media, validate_archive, validate_zip_paths
from tests.support import ProjectTestCase


class MediaArchiveTests(ProjectTestCase):
    def test_download_has_process_deadline_and_does_not_retry(self):
        with patch("asr_agent.media_setup.run_process", side_effect=SetupError("deadline")) as run:
            with self.assertRaises(SetupError):
                bootstrap_media(self.project)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["timeout"], 360)

    def test_worker_failure_is_not_reported_as_success(self):
        failed = subprocess.CompletedProcess([], 1, '{"message":"digest mismatch"}', "")
        with patch("asr_agent.media_setup.run_process", return_value=failed) as run:
            with self.assertRaisesRegex(SetupError, "digest mismatch"):
                bootstrap_media(self.project)
        run.assert_called_once()

    def test_archive_requires_expected_size_and_digest(self):
        archive = self.project.path("download.zip")
        archive.write_bytes(b"synthetic archive bytes")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        validate_archive(archive, archive.stat().st_size, digest)
        for size, expected in [(1, digest), (archive.stat().st_size, "0" * 64)]:
            with self.assertRaises(SetupError):
                validate_archive(archive, size, expected)

    def test_zip_cannot_traverse_outside_destination(self):
        archive = self.project.path("unsafe.zip")
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("../escape.txt", "synthetic")
        with zipfile.ZipFile(archive) as package, self.assertRaises(SetupError):
            validate_zip_paths(package, self.project.path("extract"))
        self.assertFalse(self.project.path("escape.txt").exists())

    def test_zip_cannot_create_symlinks(self):
        archive = self.project.path("symlink.zip")
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr(info, "../outside")
        with zipfile.ZipFile(archive) as package, self.assertRaises(SetupError):
            validate_zip_paths(package, self.project.path("extract"))
