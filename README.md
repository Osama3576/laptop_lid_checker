# Laptop Lid Checker

A small Windows desktop widget built with **PySide6** that monitors your laptop lid state and shows it in a compact floating banner.

It displays:

- **OPEN** when the laptop lid is open
- **CLOSE** when the laptop lid is closed

The widget is:

- draggable
- always on top
- rounded
- lightweight
- hidden from the taskbar
- able to remember its last position
- able to auto-start with Windows

---

## Features

- Real-time laptop lid state monitoring
- Small floating desktop banner
- Rounded clean UI
- Draggable anywhere on screen
- Remembers last position
- Starts automatically with Windows
- Hidden from taskbar
- Can be packaged into a standalone `.exe`

---

## Requirements

- Windows laptop
- Python 3.10+ recommended
- PySide6
- PyInstaller (only needed if you want to build `.exe`)

---

## Project File

For easiest build process, keep your main Python file named:

```bash
laptop_lid_checker.py
```

---

## Install Dependencies

Open terminal in your project folder and run:

```bash
pip install PySide6 pyinstaller
```

---

## Run the App with Python

Before building the EXE, test the app first:

```bash
python laptop_lid_checker.py
```

If everything is working correctly, you should see a small floating widget on your desktop showing the lid state.

---

## How to Build the EXE

Follow these steps carefully:

### Step 1: Open terminal in your project folder

Make sure your folder contains:

```bash
laptop_lid_checker.py
```

### Step 2: Install required packages

```bash
pip install PySide6 pyinstaller
```

### Step 3: Test the Python file first

```bash
python laptop_lid_checker.py
```

If the widget opens and works correctly, move to the next step.

### Step 4: Build the EXE

Run this command:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name laptop_lid_checker laptop_lid_checker.py
```

### Step 5: Wait for build to finish

After the build completes, PyInstaller will create these items automatically:

- `build/`
- `dist/`
- `laptop_lid_checker.spec`

### Step 6: Find your EXE file

Your final executable will be here:

```bash
dist\laptop_lid_checker.exe
```

### Step 7: Run the EXE

Double-click the file:

```bash
dist\laptop_lid_checker.exe
```

Or run it from terminal:

```bash
dist\laptop_lid_checker.exe
```

---

## Optional: Build EXE with Icon

If you have an icon file like `icon.ico`, use this command instead:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name laptop_lid_checker --icon=icon.ico laptop_lid_checker.py
```

---

## Recommended Build Flow

Use this order every time:

1. Write or update `laptop_lid_checker.py`
2. Test it with Python
3. Build the EXE with PyInstaller
4. Open the EXE from the `dist` folder
5. Confirm everything works correctly

---

## Output Files After Build

After building, your project folder may look like this:

```bash
your_project_folder/
│
├── laptop_lid_checker.py
├── README.md
├── build/
├── dist/
│   └── laptop_lid_checker.exe
└── laptop_lid_checker.spec
```

---

## Rebuild the EXE Cleanly

If you want to rebuild from scratch, delete these generated items first:

```bash
build
dist
laptop_lid_checker.spec
```

Then run the build command again:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name laptop_lid_checker laptop_lid_checker.py
```

---

## Troubleshooting

### EXE opens but widget does not appear
- First test the Python script directly
- Make sure PySide6 is installed correctly
- Confirm the script works before building the EXE

### EXE closes immediately
- Run the Python file first and check for errors
- If needed, temporarily test without `--windowed` to see console errors

Example:

```bash
pyinstaller --noconfirm --clean --onefile --name laptop_lid_checker laptop_lid_checker.py
```

### Rounded UI does not look correct
- Use the latest PySide6 version of the script
- Make sure you are not running an older Tkinter-based build

### Lid state does not update after closing the lid
- Some laptops go to sleep immediately when the lid closes
- In that case, the app cannot continue updating while the system is sleeping

### Startup does not work
- Run the app at least once manually
- The app should create its startup entry after launch

---

## Notes

- This app is designed for **Windows laptops only**
- It uses Windows power notifications to detect lid open/close changes
- The EXE must be built on Windows
- The app is intended to be small, simple, and always visible on top of the desktop

---

## Quick Start

### Install
```bash
pip install PySide6 pyinstaller
```

### Run with Python
```bash
python laptop_lid_checker.py
```

### Build EXE
```bash
pyinstaller --noconfirm --clean --onefile --windowed --name laptop_lid_checker laptop_lid_checker.py
```

### Open EXE
```bash
dist\laptop_lid_checker.exe
```

---

## License

Personal or custom-use project.