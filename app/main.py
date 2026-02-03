import os
import shutil
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.request import Request, urlopen
import zipfile
import tarfile

FACTORIO_URL = "https://update.clusterio.tricki.ru/files/factorio.zip"
MODS_URL = "https://update.clusterio.tricki.ru/files/mods.zip"


def human_bytes(value: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def download_file(
    url: str,
    dest_path: str,
    status_callback,
    progress_callback,
    info_callback,
) -> None:
    request = Request(url, headers={"User-Agent": "cluster-factorio-installer"})
    with urlopen(request) as response, open(dest_path, "wb") as dest:
        total = response.headers.get("Content-Length")
        total_size = int(total) if total else None
        downloaded = 0
        chunk_size = 1024 * 256
        last_time = time.perf_counter()
        last_downloaded = 0
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            dest.write(chunk)
            downloaded += len(chunk)
            percent = None
            if total_size:
                percent = downloaded / total_size * 100
                status_callback(
                    f"Загрузка: {human_bytes(downloaded)} / {human_bytes(total_size)}"
                )
                progress_callback(percent)
            else:
                status_callback(f"Загрузка: {human_bytes(downloaded)}")
                progress_callback(0)
            now = time.perf_counter()
            elapsed = now - last_time
            if elapsed >= 0.4:
                speed = (downloaded - last_downloaded) / elapsed
                info_callback(
                    downloaded,
                    total_size,
                    speed,
                    percent if total_size else None,
                )
                last_time = now
                last_downloaded = downloaded
        info_callback(downloaded, total_size, 0.0, 100.0 if total_size else None)


def extract_archive(
    archive_path: str,
    target_dir: str,
    status_callback,
    progress_callback,
    info_callback,
) -> None:
    status_callback("Распаковка архива...")
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as archive:
            members = archive.infolist()
            total = len(members)
            if total == 0:
                progress_callback(100)
                info_callback(0, 0, 0.0)
                return
            last_time = time.perf_counter()
            last_index = 0
            for index, member in enumerate(members, start=1):
                archive.extract(member, target_dir)
                progress_callback(index / total * 100)
                now = time.perf_counter()
                elapsed = now - last_time
                if elapsed >= 0.3:
                    speed = (index - last_index) / elapsed
                    info_callback(index, total, speed)
                    last_time = now
                    last_index = index
            info_callback(total, total, 0.0)
        return

    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as archive:
            members = archive.getmembers()
            total = len(members)
            if total == 0:
                progress_callback(100)
                info_callback(0, 0, 0.0)
                return
            last_time = time.perf_counter()
            last_index = 0
            for index, member in enumerate(members, start=1):
                archive.extract(member, target_dir)
                progress_callback(index / total * 100)
                now = time.perf_counter()
                elapsed = now - last_time
                if elapsed >= 0.3:
                    speed = (index - last_index) / elapsed
                    info_callback(index, total, speed)
                    last_time = now
                    last_index = index
            info_callback(total, total, 0.0)
        return

    raise ValueError("Не удалось определить формат архива.")


def sync_directory(source_dir: str, target_dir: str) -> None:
    if os.path.exists(target_dir):
        for entry in os.listdir(target_dir):
            entry_path = os.path.join(target_dir, entry)
            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path)
            else:
                os.remove(entry_path)
    else:
        os.makedirs(target_dir, exist_ok=True)

    for root, dirs, files in os.walk(source_dir):
        rel_root = os.path.relpath(root, source_dir)
        target_root = (
            target_dir if rel_root == "." else os.path.join(target_dir, rel_root)
        )
        os.makedirs(target_root, exist_ok=True)
        for directory in dirs:
            os.makedirs(os.path.join(target_root, directory), exist_ok=True)
        for file_name in files:
            src_file = os.path.join(root, file_name)
            dst_file = os.path.join(target_root, file_name)
            shutil.copy2(src_file, dst_file)


def ensure_appdata_mods_dir() -> str:
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("Не удалось определить путь %APPDATA%.")
    return os.path.join(appdata, "Factorio", "mods")


class InstallerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tricki Кластер серверов Factorio")
        self.geometry("720x420")
        self.resizable(False, False)
        self.configure(bg="#15130f")

        self.status_var = tk.StringVar(value="Готово к работе.")
        self.download_info_var = tk.StringVar(value="Скорость: — • Объем: — • 0%")
        self.extract_info_var = tk.StringVar(value="Файлы: — • 0%")
        self.download_progress = tk.DoubleVar(value=0)
        self.extract_progress = tk.DoubleVar(value=0)
        self._create_widgets()

    def _create_widgets(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Card.TFrame",
            background="#1f1a16",
        )
        style.configure(
            "Title.TLabel",
            background="#15130f",
            foreground="#f2e8d5",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#15130f",
            foreground="#d4b483",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Status.TLabel",
            background="#1f1a16",
            foreground="#f2e8d5",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 11, "bold"),
            background="#d97706",
            foreground="#1a120b",
            padding=10,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#f59e0b")],
        )
        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 11, "bold"),
            background="#9a3412",
            foreground="#fff7ed",
            padding=10,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#c2410c")],
        )
        style.configure(
            "Download.Horizontal.TProgressbar",
            troughcolor="#2a211b",
            background="#f59e0b",
        )
        style.configure(
            "Extract.Horizontal.TProgressbar",
            troughcolor="#2a211b",
            background="#f97316",
        )

        header = ttk.Frame(self, style="Card.TFrame", padding=16)
        header.pack(fill="x", padx=18, pady=(18, 8))

        title = ttk.Label(
            header,
            text="Tricki Кластер серверов Factorio",
            style="Title.TLabel",
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            header,
            text="Factorio в стиле индустриального пламени: установка и моды в один клик.",
            style="Subtitle.TLabel",
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        button_frame = ttk.Frame(self, style="Card.TFrame", padding=16)
        button_frame.pack(fill="x", padx=18, pady=8)

        install_btn = ttk.Button(
            button_frame,
            text="Установить игру",
            style="Primary.TButton",
            command=self._start_install_game,
        )
        install_btn.grid(row=0, column=0, padx=12, pady=4, sticky="ew")

        update_btn = ttk.Button(
            button_frame,
            text="Обновить моды",
            style="Secondary.TButton",
            command=self._start_update_mods,
        )
        update_btn.grid(row=0, column=1, padx=12, pady=4, sticky="ew")

        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        progress_frame = ttk.Frame(self, style="Card.TFrame", padding=16)
        progress_frame.pack(fill="x", padx=18, pady=8)

        ttk.Label(
            progress_frame,
            text="Загрузка",
            style="Status.TLabel",
        ).pack(anchor="w")
        self.download_bar = ttk.Progressbar(
            progress_frame,
            variable=self.download_progress,
            style="Download.Horizontal.TProgressbar",
            maximum=100,
        )
        self.download_bar.pack(fill="x", pady=(6, 12))

        ttk.Label(
            progress_frame,
            textvariable=self.download_info_var,
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(
            progress_frame,
            text="Распаковка",
            style="Status.TLabel",
        ).pack(anchor="w")
        self.extract_bar = ttk.Progressbar(
            progress_frame,
            variable=self.extract_progress,
            style="Extract.Horizontal.TProgressbar",
            maximum=100,
        )
        self.extract_bar.pack(fill="x", pady=(6, 0))

        ttk.Label(
            progress_frame,
            textvariable=self.extract_info_var,
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            style="Status.TLabel",
            wraplength=560,
        )
        status_label.pack(pady=(6, 0))

        info = ttk.Label(
            self,
            text=(
                "Источник: update.clusterio.tricki.ru • "
                "Моды синхронизируются в %APPDATA%\\Factorio\\mods"
            ),
            style="Subtitle.TLabel",
        )
        info.pack(pady=(0, 12))

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def _set_download_progress(self, value: float) -> None:
        self.download_progress.set(value)
        self.update_idletasks()

    def _set_download_info(
        self,
        downloaded: int,
        total: int | None,
        speed: float,
        percent: float | None,
    ) -> None:
        total_text = human_bytes(total) if total else "—"
        percent_text = f"{percent:.1f}%" if percent is not None else "—"
        speed_text = f"{human_bytes(speed)}/с" if speed else "—"
        self.download_info_var.set(
            f"Скорость: {speed_text} • Объем: {human_bytes(downloaded)} / {total_text} • {percent_text}"
        )
        self.update_idletasks()

    def _set_extract_progress(self, value: float) -> None:
        self.extract_progress.set(value)
        self.extract_info_var.set(f"Файлы: — • {value:.1f}%")
        self.update_idletasks()

    def _set_extract_info(self, extracted: int, total: int, speed: float) -> None:
        percent = extracted / total * 100 if total else 0
        speed_text = f"{speed:.1f} файл/с" if speed else "—"
        self.extract_info_var.set(
            f"Файлы: {extracted} / {total} • {percent:.1f}% • {speed_text}"
        )
        self.update_idletasks()

    def _reset_progress(self) -> None:
        self.download_progress.set(0)
        self.extract_progress.set(0)
        self.download_info_var.set("Скорость: — • Объем: — • 0%")
        self.extract_info_var.set("Файлы: — • 0%")
        self.update_idletasks()

    def _start_install_game(self) -> None:
        target_dir = filedialog.askdirectory(
            title="Выберите папку для установки Factorio"
        )
        if not target_dir:
            return
        self._reset_progress()
        threading.Thread(
            target=self._install_game,
            args=(target_dir,),
            daemon=True,
        ).start()

    def _start_update_mods(self) -> None:
        self._reset_progress()
        threading.Thread(target=self._update_mods, daemon=True).start()

    def _install_game(self, target_dir: str) -> None:
        try:
            self._set_status("Загрузка Factorio...")
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "factorio_archive")
                download_file(
                    FACTORIO_URL,
                    archive_path,
                    self._set_status,
                    self._set_download_progress,
                    self._set_download_info,
                )
                extract_archive(
                    archive_path,
                    target_dir,
                    self._set_status,
                    self._set_extract_progress,
                    self._set_extract_info,
                )
            self._set_status("Factorio установлен.")
            messagebox.showinfo("Готово", "Factorio успешно установлен.")
        except Exception as exc:  # noqa: BLE001
            self._set_status("Ошибка при установке Factorio.")
            messagebox.showerror("Ошибка", str(exc))

    def _update_mods(self) -> None:
        try:
            mods_dir = ensure_appdata_mods_dir()
            self._set_status("Загрузка модов...")
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "mods_archive")
                download_file(
                    MODS_URL,
                    archive_path,
                    self._set_status,
                    self._set_download_progress,
                    self._set_download_info,
                )
                extracted_dir = os.path.join(temp_dir, "mods")
                os.makedirs(extracted_dir, exist_ok=True)
                extract_archive(
                    archive_path,
                    extracted_dir,
                    self._set_status,
                    self._set_extract_progress,
                    self._set_extract_info,
                )
                sync_directory(extracted_dir, mods_dir)
            self._set_status("Моды синхронизированы.")
            messagebox.showinfo("Готово", "Моды успешно обновлены.")
        except Exception as exc:  # noqa: BLE001
            self._set_status("Ошибка при обновлении модов.")
            messagebox.showerror("Ошибка", str(exc))


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
