# TaskFlow v8.0

**Focus. Flow. Finish.**

TaskFlow is a privacy-first, AI-powered productivity hub designed to help you manage tasks, habits, and mental well-being without your data ever leaving your device. The AI starts on your device and stays there.

## 🚀 Features

*   **🧠 Local AI Brain:** Smart categorization and priority inference that learns from *you* (stored in `user_training.json`).
*   **🔒 Privacy First:** No cloud servers. All data lives locally in JSON files.
*   **⚡ Brain Dump:** Type anything, and the AI sorts it into Today, Tomorrow, or Someday.
*   **📊 Analytics:** GitHub-style heatmap, mood tracking, and productivity scores.
*   **🧘 Zen Mode:** Distraction-free timer for deep work.
*   **📱 Desktop Widget:** Always-on-top companion for quick access.

## 🛠️ Installation

1.  Install Python 3.10+.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the Hub:
    ```bash
    python TaskFlowHub.py
    ```

## 📦 Building (Windows)

To create a standalone `.exe`:

1.  Install PyInstaller: `pip install pyinstaller`
2.  Run the build script:
    ```bash
    python build.py
    ```
3.  (Optional) If Inno Setup is installed, it will automatically generate an installer in `Output/`.

## 📂 Data Location

Your data is stored in `%APPDATA%\TaskFlowV7`.
You can edit `knowledge_base.json` to manually teach the AI new tricks!