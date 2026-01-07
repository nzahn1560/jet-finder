#!/usr/bin/env python3
"""
Setup script for Jet Finder application.
This script helps with installation and Google Sheets setup.
"""

import sys
import subprocess
import webbrowser
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or newer is required.")
        sys.exit(1)
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def install_requirements():
    """Install required packages."""
    print("\nInstalling required packages...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✓ Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print("× Error installing dependencies.")
        sys.exit(1)


def create_directories():
    """Create required directories."""
    print("\nCreating required directories...")
    try:
        # Create data directory
        Path("static/data").mkdir(parents=True, exist_ok=True)
        print("✓ Directories created successfully.")
    except Exception as e:
        print(f"× Error creating directories: {e}")
        sys.exit(1)


def setup_google_sheets():
    """Guide user through Google Sheets setup."""
    print("\nGoogle Sheets Setup:")
    print("-------------------")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project")
    print("3. Enable the Google Sheets API for your project")
    print("4. Create OAuth 2.0 credentials (Desktop application)")
    print("5. Download the credentials as JSON")
    print("6. Save the file as 'credentials.json' in this directory")

    # Ask if user wants to open Google Cloud Console
    open_console = input("\nWould you like to open Google Cloud Console now? (y/n): ")
    if open_console.lower() == 'y':
        webbrowser.open("https://console.cloud.google.com/apis/credentials")

    # Check if credentials.json exists
    creds_path = Path("credentials.json")
    if creds_path.exists():
        print("\n✓ credentials.json found.")

        # Ask for spreadsheet ID
        sheet_id = input("\nEnter your Google Sheets Spreadsheet ID: ")
        if sheet_id:
            # Update app.py with the spreadsheet ID
            update_spreadsheet_id(sheet_id)
    else:
        print("\n× credentials.json not found.")
        print("  You'll need to create this file manually before using Google Sheets integration.")


def update_spreadsheet_id(sheet_id):
    """Update the SPREADSHEET_ID in app.py."""
    try:
        with open("app.py", "r") as f:
            content = f.read()

        # Replace the SPREADSHEET_ID line
        if "SPREADSHEET_ID = " in content:
            content = content.replace(
                "SPREADSHEET_ID = '1dGpfWvIagJnLZOJtHLq0_BziKsT6GkeASOGMvPKY9YE'",
                f"SPREADSHEET_ID = '{sheet_id}'"
            )

            with open("app.py", "w") as f:
                f.write(content)

            print("✓ Spreadsheet ID updated in app.py")
        else:
            print("× Could not find SPREADSHEET_ID in app.py")
    except Exception as e:
        print(f"× Error updating Spreadsheet ID: {e}")


def main():
    """Main function."""
    print("Jet Finder Setup")
    print("===============\n")

    check_python_version()
    install_requirements()
    create_directories()

    # Ask if user wants to set up Google Sheets
    setup_sheets = input("\nWould you like to set up Google Sheets integration? (y/n): ")
    if setup_sheets.lower() == 'y':
        setup_google_sheets()

    print("\nSetup Complete!")
    print("To start the application, run: python app.py")
    print("Then open http://localhost:8081 in your browser.")


if __name__ == "__main__":
    main()
