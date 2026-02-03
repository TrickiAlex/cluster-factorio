# Clusterio Factorio Installer

Небольшое приложение на Python (Tkinter) для установки Factorio и синхронизации модов.

## Возможности

- **Установить игру**: скачивает архив с `https://update.clusterio.tricki.ru/files/factroio.zip` и распаковывает в выбранную пользователем папку.
- **Обновить моды**: скачивает архив с `https://update.clusterio.tricki.ru/files/mods.zip` и синхронизирует содержимое в `%APPDATA%\Factorio\mods`.

## Запуск

Требуется установленный Python 3.10+.

```bash
python app/main.py
```

## Примечания

- Оба URL должны отдавать архив (zip или tar.*).
- Синхронизация модов полностью заменяет содержимое локальной папки `mods` содержимым архива.
