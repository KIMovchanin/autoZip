from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

import py7zr

from autozip.core import (
    archive_folder_name,
    build_extraction_jobs,
    discover_archives_in_directory,
    filter_supported_archives,
    run_extraction_jobs,
)


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_directory_discovery_ignores_non_archives(self) -> None:
        zip_path = self.root / "one.zip"
        self._write_zip(zip_path, "file.txt", "hello")
        (self.root / "note.txt").write_text("skip me", encoding="utf-8")

        nested_dir = self.root / "nested"
        nested_dir.mkdir()
        seven_zip_path = nested_dir / "two.7z"
        self._write_7z(seven_zip_path, "nested.txt", "inside")

        shallow = discover_archives_in_directory(self.root, recursive=False)
        recursive = discover_archives_in_directory(self.root, recursive=True)

        self.assertEqual([zip_path.resolve()], shallow)
        self.assertEqual(
            sorted([zip_path.resolve(), seven_zip_path.resolve()], key=lambda path: str(path).lower()),
            recursive,
        )

    def test_build_extraction_jobs_creates_unique_target_names(self) -> None:
        zip_path = self.root / "pack.zip"
        rar_path = self.root / "pack.rar"
        self._write_zip(zip_path, "a.txt", "1")
        rar_path.write_bytes(b"not a real rar")

        destination = self.root / "output"
        (destination / "pack").mkdir(parents=True)
        jobs = build_extraction_jobs([zip_path, rar_path], destination)

        self.assertEqual("pack-2", jobs[0].output_dir.name)
        self.assertEqual("pack-3", jobs[1].output_dir.name)

    def test_run_extraction_jobs_handles_zip_and_7z(self) -> None:
        zip_path = self.root / "alpha.zip"
        seven_zip_path = self.root / "beta.7z"
        self._write_zip(zip_path, "alpha.txt", "zip data")
        self._write_7z(seven_zip_path, "beta.txt", "7z data")

        sequential_jobs = build_extraction_jobs([zip_path], self.root / "sequential")
        sequential_results = run_extraction_jobs(sequential_jobs, parallel=False)

        self.assertTrue(sequential_results[0].success)
        self.assertEqual(
            "zip data",
            (sequential_jobs[0].output_dir / "alpha.txt").read_text(encoding="utf-8"),
        )

        parallel_jobs = build_extraction_jobs([zip_path, seven_zip_path], self.root / "parallel")
        parallel_results = run_extraction_jobs(parallel_jobs, parallel=True, max_workers=2)

        self.assertEqual(2, len(parallel_results))
        self.assertTrue(all(result.success for result in parallel_results))
        self.assertEqual(
            "zip data",
            (parallel_jobs[0].output_dir / "alpha.txt").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "7z data",
            (parallel_jobs[1].output_dir / "beta.txt").read_text(encoding="utf-8"),
        )

    def test_filter_supported_archives_keeps_only_valid_files(self) -> None:
        zip_path = self.root / "ok.zip"
        txt_path = self.root / "bad.txt"
        self._write_zip(zip_path, "x.txt", "ok")
        txt_path.write_text("bad", encoding="utf-8")

        filtered = filter_supported_archives([zip_path, txt_path])

        self.assertEqual([zip_path.resolve()], filtered)
        self.assertEqual("ok", archive_folder_name(zip_path))

    @staticmethod
    def _write_zip(path: Path, filename: str, content: str) -> None:
        with zipfile.ZipFile(path, mode="w") as archive_file:
            archive_file.writestr(filename, content)

    @staticmethod
    def _write_7z(path: Path, filename: str, content: str) -> None:
        source_file = path.parent / filename
        source_file.write_text(content, encoding="utf-8")
        with py7zr.SevenZipFile(path, mode="w") as archive_file:
            archive_file.write(source_file, arcname=filename)
        source_file.unlink()


if __name__ == "__main__":
    unittest.main()
