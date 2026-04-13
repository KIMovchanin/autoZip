from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import time
import zipfile

import py7zr

SUPPORTED_ARCHIVE_PATTERNS = (
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tgz",
    ".tbz2",
    ".txz",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
)

WINDOWS_7ZIP_CANDIDATES = (
    Path(r"C:\Program Files\7-Zip\7z.exe"),
    Path(r"C:\Program Files\7-Zip\7zz.exe"),
    Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    Path(r"C:\Program Files (x86)\7-Zip\7zz.exe"),
)


@dataclass(frozen=True)
class ExtractionJob:
    archive_path: Path
    archive_type: str
    output_dir: Path


@dataclass(frozen=True)
class ExtractionResult:
    archive_path: Path
    archive_type: str
    output_dir: Path
    success: bool
    message: str
    duration_seconds: float


def detect_archive_type(path: Path) -> str | None:
    archive_name = path.name.lower()
    for pattern in SUPPORTED_ARCHIVE_PATTERNS:
        if archive_name.endswith(pattern):
            return pattern
    return None


def is_supported_archive(path: Path) -> bool:
    return path.is_file() and detect_archive_type(path) is not None


def filter_supported_archives(paths: list[Path]) -> list[Path]:
    archives = [path.resolve() for path in paths if is_supported_archive(path)]
    return sorted(dict.fromkeys(archives), key=lambda path: str(path).lower())


def discover_archives_in_directory(directory: Path, recursive: bool = False) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    iterator = directory.rglob("*") if recursive else directory.iterdir()
    archives = [path.resolve() for path in iterator if is_supported_archive(path)]
    return sorted(dict.fromkeys(archives), key=lambda path: str(path).lower())


def archive_folder_name(path: Path) -> str:
    archive_type = detect_archive_type(path)
    if archive_type is None:
        return path.stem or "archive"
    folder_name = path.name[: -len(archive_type)]
    return folder_name or path.stem or "archive"


def build_extraction_jobs(archives: list[Path], destination_root: Path) -> list[ExtractionJob]:
    jobs: list[ExtractionJob] = []
    reserved_names: set[str] = set()
    destination_root = destination_root.resolve()

    for archive_path in filter_supported_archives(archives):
        base_name = archive_folder_name(archive_path)
        candidate_name = base_name
        suffix_index = 2

        while (
            candidate_name.lower() in reserved_names
            or (destination_root / candidate_name).exists()
        ):
            candidate_name = f"{base_name}-{suffix_index}"
            suffix_index += 1

        reserved_names.add(candidate_name.lower())
        jobs.append(
            ExtractionJob(
                archive_path=archive_path,
                archive_type=detect_archive_type(archive_path) or "",
                output_dir=destination_root / candidate_name,
            )
        )

    return jobs


def find_seven_zip_executable() -> Path | None:
    for command_name in ("7z", "7zz"):
        command_path = shutil.which(command_name)
        if command_path:
            return Path(command_path)

    for candidate in WINDOWS_7ZIP_CANDIDATES:
        if candidate.exists():
            return candidate

    return None


def rar_backend_message() -> str | None:
    if find_seven_zip_executable() is None:
        return (
            "RAR архивы требуют установленный 7-Zip. Приложение ищет 7z.exe "
            "в PATH и в стандартных папках Windows."
        )
    return None


def extract_archive(job: ExtractionJob, seven_zip_path: Path | None = None) -> ExtractionResult:
    started_at = time.perf_counter()
    job.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if job.archive_type == ".zip":
            with zipfile.ZipFile(job.archive_path, "r") as archive_file:
                archive_file.extractall(job.output_dir)
        elif job.archive_type == ".7z":
            with py7zr.SevenZipFile(job.archive_path, mode="r") as archive_file:
                archive_file.extractall(path=job.output_dir)
        elif job.archive_type == ".rar":
            _extract_rar_with_7zip(job, seven_zip_path or find_seven_zip_executable())
        else:
            shutil.unpack_archive(str(job.archive_path), str(job.output_dir))

        return ExtractionResult(
            archive_path=job.archive_path,
            archive_type=job.archive_type,
            output_dir=job.output_dir,
            success=True,
            message="Распаковка завершена.",
            duration_seconds=time.perf_counter() - started_at,
        )
    except Exception as exc:  # noqa: BLE001 - conversion to user-facing message
        return ExtractionResult(
            archive_path=job.archive_path,
            archive_type=job.archive_type,
            output_dir=job.output_dir,
            success=False,
            message=str(exc),
            duration_seconds=time.perf_counter() - started_at,
        )


def run_extraction_jobs(
    jobs: list[ExtractionJob],
    parallel: bool = False,
    max_workers: int | None = None,
    progress_callback=None,
) -> list[ExtractionResult]:
    if not jobs:
        return []

    seven_zip_path = find_seven_zip_executable()
    results: list[ExtractionResult] = []

    def emit(event_name: str, payload) -> None:
        if progress_callback is not None:
            progress_callback(event_name, payload)

    if not parallel:
        for job in jobs:
            emit("started", job)
            result = extract_archive(job, seven_zip_path)
            results.append(result)
            emit("finished", result)
        return results

    worker_count = max_workers or min(len(jobs), max(2, os.cpu_count() or 2))
    worker_count = max(1, min(worker_count, len(jobs)))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {}
        for job in jobs:
            emit("started", job)
            future_map[executor.submit(extract_archive, job, seven_zip_path)] = job

        for future in as_completed(future_map):
            result = future.result()
            results.append(result)
            emit("finished", result)

    results.sort(key=lambda item: str(item.archive_path).lower())
    return results


def _extract_rar_with_7zip(job: ExtractionJob, seven_zip_path: Path | None) -> None:
    if seven_zip_path is None:
        raise RuntimeError(rar_backend_message() or "RAR backend is unavailable.")

    command = [
        str(seven_zip_path),
        "x",
        str(job.archive_path),
        f"-o{job.output_dir}",
        "-y",
    ]

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
        creationflags=creation_flags,
    )

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "Неизвестная ошибка 7-Zip."
        raise RuntimeError(details)
