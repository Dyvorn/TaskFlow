# TaskFlow

A modern, clean, and robust productivity workspace designed to help you organize your tasks. Version 10.0 (The Remake) focuses on a highly responsive PyQt6 dashboard and a rock-solid SQLite backend.

## Features

### Core Functionality
- **Task Management**: Create, organize, prioritize (starred), and track your tasks across different timelines (Today, Tomorrow, This Week, Someday).
- **Modern UI**: A responsive, sleek PyQt6 interface featuring a clean sidebar navigation and contextual dashboard view.
- **Robust Data Storage**: SQLite-powered backend with safe transaction context managers, ensuring your data is never lost.
- **Clean Architecture**: A thoroughly refactored, modular codebase separating UI components from core business logic.

*(Note: Advanced features like AI Coach, Voice Commands, and Zen Mode from earlier versions are currently archived in `_legacy_code/` and are planned for integration in future updates.)*

## Project Structure

```
TaskFlow/
├── src/                  # Main application source code
│   ├── main.py           # Application entry point
│   ├── core/             # Database connection and task logic
│   └── ui/               # PyQt6 widgets, windows, and styles
├── tests/                # Automated test scripts (e.g., test_db.py)
├── data/                 # Database storage (taskflow.db)
├── assets/               # Media and image assets
├── _legacy_code/         # Archived code from v9.0
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Getting Started

### Prerequisites
- Python 3.x
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Dyvorn/TaskFlow.git
cd TaskFlow
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

To launch the main application interface, run:
```bash
python src/main.py
```

### Running Tests

To verify your database connection and task logic:
```bash
python tests/test_db.py
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source. See the LICENSE file for details.

## Authors

**Refined** - Developer and Creator
**Craft2Fun** - Developer and Contributor

## Support

For issues, questions, or suggestions, please open an issue on GitHub or contact the development team.