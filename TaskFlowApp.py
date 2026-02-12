# ============================================================================
# TASKFLOW V7.0 - UNIFIED APPLICATION ENTRYPOINT
# ============================================================================

import sys
import argparse

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from taskflowmodel import (
    get_data_paths,
    load_state,
    save_state,
    rollover_tasks,
)
from TaskFlowHub import HubWindow, SplashWindow
from TaskFlowWidget import WidgetWindow


def main() -> None:
    """
    Main entry point for the unified TaskFlow application.
    Handles CLI arguments, state loading, and window creation.
    """
    parser = argparse.ArgumentParser(description="TaskFlow Hub & Widget")
    parser.add_argument("--no-widget", action="store_true", help="Launch the Hub without the Widget.")
    parser.add_argument("--widget-only", action="store_true", help="Launch only the Widget for debugging.")
    parser.add_argument(
        "--page",
        choices=["home", "today", "week", "someday", "projects", "stats", "settings"],
        default="home",
        help="Specify the page the Hub should open on startup.",
    )
    args = parser.parse_args()

    # --- State Loading & Pre-flight ---
    paths = get_data_paths()
    state = load_state(paths)
    rollover_tasks(state)
    save_state(paths, state)  # Persist rollover changes immediately

    # --- Application Setup ---
    app = QApplication(sys.argv)

    hub = None
    widget = None

    # --- Window Creation ---
    if not args.widget_only:
        hub = HubWindow(state, paths)
        hub.open_page(args.page)

    if not args.no_widget and state.get("settings", {}).get("widgetEnabled", True):
        # The widget needs the hub to trigger saves and open pages
        if not hub:
            # This case happens with --widget-only, so we need a dummy hub or save function
            # For simplicity, we'll just assume if hub doesn't exist, saving is direct.
            # A better approach would be a dedicated save manager, but this fits the requirements.
            save_callback = lambda: save_state(paths, state)
            hub_ref = None
        else:
            save_callback = hub.schedule_save
            hub_ref = hub

        widget = WidgetWindow(state, paths, save_callback, hub_ref)
        if hub:
            hub.data_changed.connect(widget._refresh_tasks)

    # --- Show Windows ---
    if hub:
        splash = SplashWindow()
        splash.show()

        def show_hub():
            if state.get("settings", {}).get("startWithHubMaximized", True):
                hub.showMaximized()
            else:
                hub.show()
            if widget:
                widget.show()

        QTimer.singleShot(1200, show_hub) # Match splash screen duration
    elif widget:
        widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()