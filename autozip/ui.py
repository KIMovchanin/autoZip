from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import (
    ExtractionJob,
    ExtractionResult,
    build_extraction_jobs,
    detect_archive_type,
    discover_archives_in_directory,
    filter_supported_archives,
    find_seven_zip_executable,
    rar_backend_message,
    run_extraction_jobs,
)


class AutoZipApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("autoZip")
        self.geometry("1080x720")
        self.minsize(920, 620)
        self.configure(bg="#efe7dc")

        self.selected_files: list[Path] = []
        self.selected_folder: Path | None = None
        self.excluded_archives: set[Path] = set()
        self.preview_jobs: list[ExtractionJob] = []
        self.event_queue = Queue()
        self.running = False

        default_workers = min(4, max(2, os.cpu_count() or 2))
        self.source_summary_var = tk.StringVar(value="Источник не выбран.")
        self.destination_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.mode_var = tk.StringVar(value="sequential")
        self.parallel_workers_var = tk.IntVar(value=default_workers)
        self.notice_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Выберите архивы или папку с архивами.")
        self.progress_text_var = tk.StringVar(value="0 из 0")

        self._configure_style()
        self._build_ui()
        self._refresh_notice()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Root.TFrame", background="#efe7dc")
        style.configure("Card.TFrame", background="#faf7f1", relief="flat")
        style.configure("Card.TLabelframe", background="#faf7f1")
        style.configure("Card.TLabelframe.Label", background="#faf7f1", foreground="#2e2a24")
        style.configure("Title.TLabel", background="#efe7dc", foreground="#221d18", font=("Segoe UI", 20, "bold"))
        style.configure("Body.TLabel", background="#faf7f1", foreground="#2e2a24", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#faf7f1", foreground="#6c6256", font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _build_ui(self) -> None:
        container = ttk.Frame(self, style="Root.TFrame", padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(2, weight=1)

        header = ttk.Frame(container, style="Root.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Label(header, text="autoZip", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Выберите архивы или папку, затем укажите место распаковки и режим запуска.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        left_card = ttk.LabelFrame(container, text="Источник", style="Card.TLabelframe", padding=14)
        left_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 12))
        left_card.columnconfigure(0, weight=1)

        buttons_frame = ttk.Frame(left_card, style="Card.TFrame")
        buttons_frame.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            buttons_frame,
            text="Выбрать архивы",
            style="Accent.TButton",
            command=self._choose_archives,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ttk.Button(
            buttons_frame,
            text="Выбрать папку",
            style="Accent.TButton",
            command=self._choose_folder,
        ).grid(row=0, column=1, padx=(0, 8), sticky="w")
        ttk.Button(buttons_frame, text="Очистить", command=self._clear_source).grid(row=0, column=2, sticky="w")

        ttk.Label(
            left_card,
            textvariable=self.source_summary_var,
            style="Body.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(12, 8))
        ttk.Checkbutton(
            left_card,
            text="Искать архивы в подпапках",
            variable=self.recursive_var,
            command=self._refresh_preview,
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(
            left_card,
            text="Поддерживаются ZIP, 7Z, RAR и tar-архивы. При выборе папки будут учитываться только архивы.",
            style="Muted.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(10, 0))

        right_card = ttk.LabelFrame(container, text="Настройки", style="Card.TLabelframe", padding=14)
        right_card.grid(row=1, column=1, sticky="nsew", pady=(0, 12))
        right_card.columnconfigure(0, weight=1)

        destination_row = ttk.Frame(right_card, style="Card.TFrame")
        destination_row.grid(row=0, column=0, sticky="ew")
        destination_row.columnconfigure(0, weight=1)
        ttk.Label(destination_row, text="Куда распаковывать", style="Body.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        destination_entry = ttk.Entry(destination_row, textvariable=self.destination_var)
        destination_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 8))
        ttk.Button(destination_row, text="Обзор", command=self._choose_destination).grid(row=1, column=1, pady=(8, 0))
        destination_entry.bind("<KeyRelease>", lambda _: self._refresh_preview())

        mode_frame = ttk.Frame(right_card, style="Card.TFrame")
        mode_frame.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(mode_frame, text="Режим распаковки", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            mode_frame,
            text="Поочередно",
            value="sequential",
            variable=self.mode_var,
            command=self._refresh_notice,
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Radiobutton(
            mode_frame,
            text="Параллельно",
            value="parallel",
            variable=self.mode_var,
            command=self._refresh_notice,
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        workers_row = ttk.Frame(right_card, style="Card.TFrame")
        workers_row.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        ttk.Label(workers_row, text="Количество одновременных задач", style="Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Spinbox(
            workers_row,
            from_=2,
            to=max(2, os.cpu_count() or 2),
            textvariable=self.parallel_workers_var,
            width=6,
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        ttk.Label(
            right_card,
            textvariable=self.notice_var,
            style="Muted.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(18, 0))

        action_row = ttk.Frame(right_card, style="Card.TFrame")
        action_row.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        self.run_button = ttk.Button(
            action_row,
            text="Запустить распаковку",
            style="Accent.TButton",
            command=self._start_extraction,
        )
        self.run_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Button(action_row, text="Убрать из списка", command=self._remove_selected_archives).grid(
            row=0, column=1, sticky="w", padx=(0, 8)
        )
        ttk.Button(action_row, text="Обновить список", command=self._refresh_preview).grid(row=0, column=2, sticky="w")

        preview_card = ttk.LabelFrame(container, text="Список задач", style="Card.TLabelframe", padding=14)
        preview_card.grid(row=2, column=0, columnspan=2, sticky="nsew")
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(0, weight=1)

        columns = ("archive", "type", "target", "status", "message")
        self.tree = ttk.Treeview(preview_card, columns=columns, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("archive", text="Архив")
        self.tree.heading("type", text="Формат")
        self.tree.heading("target", text="Папка назначения")
        self.tree.heading("status", text="Статус")
        self.tree.heading("message", text="Сообщение")
        self.tree.column("archive", width=240)
        self.tree.column("type", width=80, anchor="center")
        self.tree.column("target", width=280)
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("message", width=260)
        self.tree.bind("<Delete>", lambda _: self._remove_selected_archives())

        scrollbar = ttk.Scrollbar(preview_card, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(container, style="Root.TFrame")
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel", wraplength=720).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(footer, textvariable=self.progress_text_var, style="Muted.TLabel").grid(row=0, column=1, sticky="e")

        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _choose_archives(self) -> None:
        filetypes = [
            ("Архивы", "*.zip *.7z *.rar *.tar *.tar.gz *.tar.bz2 *.tar.xz *.tgz *.tbz2 *.txz"),
            ("Все файлы", "*.*"),
        ]
        raw_paths = filedialog.askopenfilenames(title="Выберите архивы", filetypes=filetypes)
        if not raw_paths:
            return
        self.selected_files = [Path(path) for path in raw_paths]
        self.selected_folder = None
        self.excluded_archives.clear()
        self._refresh_preview()

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="Выберите папку с архивами")
        if not selected:
            return
        self.selected_folder = Path(selected)
        self.selected_files = []
        self.excluded_archives.clear()
        self._refresh_preview()

    def _choose_destination(self) -> None:
        selected = filedialog.askdirectory(title="Куда распаковать архивы")
        if not selected:
            return
        self.destination_var.set(selected)
        self._refresh_preview()

    def _clear_source(self) -> None:
        self.selected_files = []
        self.selected_folder = None
        self.excluded_archives.clear()
        self.preview_jobs = []
        self.source_summary_var.set("Источник не выбран.")
        self.status_var.set("Выберите архивы или папку с архивами.")
        self.progress.configure(maximum=0, value=0)
        self.progress_text_var.set("0 из 0")
        self._clear_tree()
        self._refresh_notice()

    def _refresh_preview(self) -> None:
        archives = self._collect_archives()
        destination_text = self.destination_var.get().strip()
        destination_root = Path(destination_text) if destination_text else Path.cwd() / "__preview__"
        self.preview_jobs = build_extraction_jobs(archives, destination_root)
        self._fill_tree(self.preview_jobs, destination_missing=not destination_text)

        if not archives:
            self.status_var.set("Подходящие архивы не найдены.")
        else:
            self.status_var.set(f"Найдено архивов: {len(archives)}.")

        self.progress.configure(maximum=len(self.preview_jobs), value=0)
        self.progress_text_var.set(f"0 из {len(self.preview_jobs)}")
        self._refresh_notice()

    def _collect_archives(self) -> list[Path]:
        if self.selected_folder is not None:
            archives = discover_archives_in_directory(self.selected_folder, recursive=self.recursive_var.get())
            archives = [path for path in archives if path not in self.excluded_archives]
            if self.recursive_var.get():
                scope_text = "с подпапками"
            else:
                scope_text = "без подпапок"
            self.source_summary_var.set(
                f"Папка: {self.selected_folder}\nНайдено архивов ({scope_text}): {len(archives)}"
            )
            return archives

        if self.selected_files:
            archives = filter_supported_archives(self.selected_files)
            archives = [path for path in archives if path not in self.excluded_archives]
            ignored = len(self.selected_files) - len(archives)
            self.source_summary_var.set(
                f"Выбрано файлов: {len(self.selected_files)}. Подходящих архивов: {len(archives)}. "
                f"Пропущено неподходящих: {ignored}."
            )
            return archives

        self.source_summary_var.set("Источник не выбран.")
        return []

    def _refresh_notice(self) -> None:
        notes = []
        if self.mode_var.get() == "parallel":
            notes.append("Параллельный режим может сильно нагружать процессор и диск.")

        has_rar = any(detect_archive_type(job.archive_path) == ".rar" for job in self.preview_jobs)
        if has_rar:
            backend_message = rar_backend_message()
            if backend_message:
                notes.append(backend_message)
            else:
                seven_zip_path = find_seven_zip_executable()
                notes.append(f"RAR будет распакован через 7-Zip: {seven_zip_path}")

        if not notes:
            notes.append("Каждый архив будет распакован в отдельную подпапку внутри выбранного каталога.")

        self.notice_var.set("\n".join(notes))

    def _fill_tree(self, jobs: list[ExtractionJob], destination_missing: bool) -> None:
        self._clear_tree()
        for job in jobs:
            target_text = job.output_dir.name if destination_missing else str(job.output_dir)
            self.tree.insert(
                "",
                "end",
                iid=str(job.archive_path),
                values=(
                    job.archive_path.name,
                    job.archive_type,
                    target_text,
                    "Ожидает",
                    "",
                ),
            )

    def _clear_tree(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def _remove_selected_archives(self) -> None:
        if self.running:
            return

        selected_items = self.tree.selection()
        if not selected_items:
            return

        self.excluded_archives.update(Path(item_id) for item_id in selected_items)
        self._refresh_preview()
        self.status_var.set(f"Убрано из списка: {len(selected_items)}.")

    def _start_extraction(self) -> None:
        if self.running:
            return

        destination_text = self.destination_var.get().strip()
        if not destination_text:
            messagebox.showerror("Нет папки назначения", "Сначала выберите папку, в которую нужно распаковать архивы.")
            return

        archives = self._collect_archives()
        if not archives:
            messagebox.showerror("Нет архивов", "Не удалось найти подходящие архивы для распаковки.")
            return

        destination_root = Path(destination_text)
        self.preview_jobs = build_extraction_jobs(archives, destination_root)
        self._fill_tree(self.preview_jobs, destination_missing=False)

        parallel = self.mode_var.get() == "parallel"
        workers = max(2, self.parallel_workers_var.get()) if parallel else 1

        if parallel:
            proceed = messagebox.askokcancel(
                "Параллельная распаковка",
                "Параллельная распаковка может сильно нагрузить компьютер. Продолжить?",
            )
            if not proceed:
                return

        self.running = True
        self.run_button.configure(state="disabled")
        self.progress.configure(maximum=len(self.preview_jobs), value=0)
        self.progress_text_var.set(f"0 из {len(self.preview_jobs)}")
        self.status_var.set("Распаковка запущена.")

        worker = threading.Thread(
            target=self._run_extraction_worker,
            args=(self.preview_jobs, parallel, workers),
            daemon=True,
        )
        worker.start()
        self.after(100, self._poll_events)

    def _run_extraction_worker(self, jobs: list[ExtractionJob], parallel: bool, workers: int) -> None:
        try:
            results = run_extraction_jobs(
                jobs,
                parallel=parallel,
                max_workers=workers,
                progress_callback=lambda event, payload: self.event_queue.put(
                    {"event": event, "payload": payload}
                ),
            )
            self.event_queue.put({"event": "completed", "payload": results})
        except Exception as exc:  # noqa: BLE001 - UI needs a user-facing message
            self.event_queue.put({"event": "fatal", "payload": str(exc)})

    def _poll_events(self) -> None:
        processed_any = False
        while True:
            try:
                event = self.event_queue.get_nowait()
            except Empty:
                break
            processed_any = True
            self._handle_event(event)

        if self.running or processed_any:
            self.after(100, self._poll_events)

    def _handle_event(self, event: dict) -> None:
        event_name = event["event"]
        payload = event["payload"]

        if event_name == "started":
            job: ExtractionJob = payload
            self._set_row(job.archive_path, status="В работе", message="Распаковка началась.")
            return

        if event_name == "finished":
            result: ExtractionResult = payload
            status_text = "Готово" if result.success else "Ошибка"
            self._set_row(result.archive_path, status=status_text, message=result.message)
            completed = sum(
                1
                for item_id in self.tree.get_children()
                if self.tree.set(item_id, "status") in {"Готово", "Ошибка"}
            )
            self.progress.configure(value=completed)
            self.progress_text_var.set(f"{completed} из {len(self.preview_jobs)}")
            return

        if event_name == "completed":
            results: list[ExtractionResult] = payload
            self.running = False
            self.run_button.configure(state="normal")
            successful = sum(1 for result in results if result.success)
            failed = len(results) - successful
            self.status_var.set(f"Распаковка завершена. Успешно: {successful}, с ошибками: {failed}.")
            if failed:
                messagebox.showwarning(
                    "Распаковка завершена с ошибками",
                    f"Успешно: {successful}. С ошибками: {failed}. Подробности показаны в таблице.",
                )
            else:
                messagebox.showinfo("Готово", f"Все архивы распакованы: {successful}.")
            return

        if event_name == "fatal":
            self.running = False
            self.run_button.configure(state="normal")
            self.status_var.set("Распаковка прервана из-за внутренней ошибки.")
            messagebox.showerror("Ошибка", payload)

    def _set_row(self, archive_path: Path, status: str, message: str) -> None:
        item_id = str(archive_path)
        if not self.tree.exists(item_id):
            return
        current_values = list(self.tree.item(item_id, "values"))
        current_values[3] = status
        current_values[4] = message
        self.tree.item(item_id, values=current_values)


def run_app() -> None:
    app = AutoZipApp()
    app.mainloop()
