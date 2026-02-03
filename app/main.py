import os
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.request import Request, urlopen
import zipfile
import tarfile

FACTORIO_URL = "https://update.clusterio.tricki.ru/files/factroio.zip"
MODS_URL = "https://update.clusterio.tricki.ru/files/mods.zip"


def human_bytes(value: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def download_file(url: str, dest_path: str, status_callback) -> None:
    request = Request(url, headers={"User-Agent": "cluster-factorio-installer"})
    with urlopen(request) as response, open(dest_path, "wb") as dest:
        total = response.headers.get("Content-Length")
        total_size = int(total) if total else None
        downloaded = 0
        chunk_size = 1024 * 256
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            dest.write(chunk)
            downloaded += len(chunk)
            if total_size:
                status_callback(
                    f"Загрузка: {human_bytes(downloaded)} / {human_bytes(total_size)}"
                )
            else:
                status_callback(f"Загрузка: {human_bytes(downloaded)}")


def extract_archive(archive_path: str, target_dir: str, status_callback) -> None:
    status_callback("Распаковка архива...")
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(target_dir)
        return

    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as archive:
            archive.extractall(target_dir)
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
        self.title("Clusterio Factorio Installer")
        self.geometry("520x260")
        self.resizable(False, False)

        self.status_var = tk.StringVar(value="Готово к работе.")
        self._create_widgets()

    def _create_widgets(self) -> None:
        title = tk.Label(
            self,
            text="Установка Factorio и синхронизация модов",
            font=("Segoe UI", 12, "bold"),
        )
        title.pack(pady=16)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=8)

        install_btn = tk.Button(
            button_frame,
            text="Установить игру",
            width=24,
            command=self._start_install_game,
        )
        install_btn.grid(row=0, column=0, padx=12)

        update_btn = tk.Button(
            button_frame,
            text="Обновить моды",
            width=24,
            command=self._start_update_mods,
        )
        update_btn.grid(row=0, column=1, padx=12)

        status_label = tk.Label(self, textvariable=self.status_var, wraplength=480)
        status_label.pack(pady=18)

        info = tk.Label(
            self,
            text=(
                "Источник: update.clusterio.tricki.ru\n"
                "Моды будут синхронизированы в %APPDATA%\\Factorio\\mods"
            ),
            fg="#555",
        )
        info.pack(pady=4)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def _start_install_game(self) -> None:
        target_dir = filedialog.askdirectory(
            title="Выберите папку для установки Factorio"
        )
        if not target_dir:
            return
        threading.Thread(
            target=self._install_game,
            args=(target_dir,),
            daemon=True,
        ).start()

    def _start_update_mods(self) -> None:
        threading.Thread(target=self._update_mods, daemon=True).start()

    def _install_game(self, target_dir: str) -> None:
        try:
            self._set_status("Загрузка Factorio...")
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "factorio_archive")
                download_file(FACTORIO_URL, archive_path, self._set_status)
                extract_archive(archive_path, target_dir, self._set_status)
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
                download_file(MODS_URL, archive_path, self._set_status)
                extracted_dir = os.path.join(temp_dir, "mods")
                os.makedirs(extracted_dir, exist_ok=True)
                extract_archive(archive_path, extracted_dir, self._set_status)
                sync_directory(extracted_dir, mods_dir)
            self._set_status("Моды синхронизированы.")
            messagebox.showinfo("Готово", "Моды успешно обновлены.")
        except Exception as exc:  # noqa: BLE001
            self._set_status("Ошибка при обновлении модов.")
            messagebox.showerror("Ошибка", str(exc))


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
