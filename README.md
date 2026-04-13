# autoZip

[ENG](#english) | [RUS](#russian)

## English

### Overview

`autoZip` is a small desktop app built with `tkinter` for batch archive extraction on Windows.

It lets the user:
- select one or more archive files manually;
- select a folder that contains archives;
- automatically ignore unsupported and non-archive files;
- choose sequential or parallel extraction;
- choose the destination folder for extracted content;
- see task status directly in the UI.

Each archive is extracted into its own subfolder inside the selected destination directory.

### Supported Formats

The app currently supports:
- `zip`
- `7z`
- `rar`
- `tar`
- `tar.gz`
- `tar.bz2`
- `tar.xz`
- `tgz`
- `tbz2`
- `txz`

### How It Works

There are two main input modes:
- file selection mode: the user picks specific archive files;
- folder selection mode: the app scans the selected folder and keeps only supported archives.

If a folder is selected, regular files such as `.txt`, `.jpg`, `.docx`, and other unsupported files are ignored automatically.

The extraction mode can be:
- sequential: safer and lighter for most computers;
- parallel: faster for large batches, but it can heavily load CPU and disk.

### RAR Support

`RAR` extraction requires `7-Zip` to be installed on the machine.

The app looks for `7z.exe` in:
- system `PATH`
- `C:\Program Files\7-Zip\7z.exe`
- `C:\Program Files\7-Zip\7zz.exe`
- `C:\Program Files (x86)\7-Zip\7z.exe`
- `C:\Program Files (x86)\7-Zip\7zz.exe`

`ZIP` and `7Z` extraction work directly through Python dependencies.

### Project Structure

- [main.py](D:/JetBrains/PycharmProjects/autoZip/main.py): application entry point
- [autozip/core.py](D:/JetBrains/PycharmProjects/autoZip/autozip/core.py): archive discovery and extraction logic
- [autozip/ui.py](D:/JetBrains/PycharmProjects/autoZip/autozip/ui.py): `tkinter` desktop interface
- [tests/test_core.py](D:/JetBrains/PycharmProjects/autoZip/tests/test_core.py): core tests
- [requirements.txt](D:/JetBrains/PycharmProjects/autoZip/requirements.txt): Python dependencies

### Requirements

- Windows
- Python `3.9+`
- optional: installed `7-Zip` for `RAR` extraction

### Run From Source

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the app:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Run Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Build EXE

Install `PyInstaller`:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
```

Build a single Windows executable:

```powershell
.\.venv\Scripts\pyinstaller.exe --onefile --windowed --name autoZip main.py
```

The built executable will appear in:

```text
dist\autoZip.exe
```

### Notes

- Parallel extraction is useful, but it may significantly increase CPU and disk usage.
- Unsigned `.exe` files may trigger Windows SmartScreen warnings on other computers.
- A self-signed certificate is free, but it will not be trusted by default on another machine.

## Russian

### Обзор

`autoZip` — это небольшое desktop-приложение на `tkinter` для пакетной распаковки архивов в Windows.

Программа позволяет:
- выбрать один или несколько архивов вручную;
- выбрать папку, в которой лежат архивы;
- автоматически игнорировать неподходящие и неархивные файлы;
- выбрать последовательную или параллельную распаковку;
- указать папку, куда нужно распаковать содержимое;
- видеть статусы задач прямо в интерфейсе.

Каждый архив распаковывается в отдельную подпапку внутри выбранной папки назначения.

### Поддерживаемые Форматы

Сейчас поддерживаются:
- `zip`
- `7z`
- `rar`
- `tar`
- `tar.gz`
- `tar.bz2`
- `tar.xz`
- `tgz`
- `tbz2`
- `txz`

### Как Это Работает

Есть два основных сценария выбора источника:
- режим выбора файлов: пользователь вручную отмечает нужные архивы;
- режим выбора папки: программа сканирует выбранную папку и оставляет только поддерживаемые архивы.

Если пользователь выбирает папку, обычные файлы вроде `.txt`, `.jpg`, `.docx` и любые другие неподходящие форматы автоматически пропускаются.

Режим распаковки может быть таким:
- последовательный: безопаснее и легче для большинства компьютеров;
- параллельный: быстрее для больших наборов архивов, но может сильно нагрузить процессор и диск.

### Поддержка RAR

Для распаковки `RAR` нужен установленный `7-Zip`.

Приложение ищет `7z.exe` в:
- системной переменной `PATH`
- `C:\Program Files\7-Zip\7z.exe`
- `C:\Program Files\7-Zip\7zz.exe`
- `C:\Program Files (x86)\7-Zip\7z.exe`
- `C:\Program Files (x86)\7-Zip\7zz.exe`

`ZIP` и `7Z` распаковываются напрямую через Python-зависимости.

### Структура Проекта

- [main.py](D:/JetBrains/PycharmProjects/autoZip/main.py): точка входа приложения
- [autozip/core.py](D:/JetBrains/PycharmProjects/autoZip/autozip/core.py): логика поиска архивов и распаковки
- [autozip/ui.py](D:/JetBrains/PycharmProjects/autoZip/autozip/ui.py): desktop-интерфейс на `tkinter`
- [tests/test_core.py](D:/JetBrains/PycharmProjects/autoZip/tests/test_core.py): тесты ядра
- [requirements.txt](D:/JetBrains/PycharmProjects/autoZip/requirements.txt): зависимости Python

### Требования

- Windows
- Python `3.9+`
- опционально: установленный `7-Zip` для распаковки `RAR`

### Запуск Из Исходников

Установка зависимостей:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Запуск приложения:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Запуск Тестов

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Сборка EXE

Установка `PyInstaller`:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
```

Сборка одного Windows `.exe`:

```powershell
.\.venv\Scripts\pyinstaller.exe --onefile --windowed --name autoZip main.py
```

Готовый файл появится здесь:

```text
dist\autoZip.exe
```

### Примечания

- Параллельная распаковка удобна, но может заметно увеличить нагрузку на процессор и диск.
- Неподписанные `.exe` файлы могут вызывать предупреждения Windows SmartScreen на другом компьютере.
- Самоподписанный сертификат бесплатен, но по умолчанию не будет считаться доверенным на чужом ПК.
