"""
package_lambda.py

Builds a production-ready AWS Lambda deployment ZIP package for the
AI Thumbnail Generator FastAPI application.

Targets:
  - AWS Lambda Managed Runtime: Python 3.12 (x86_64)
  - Handler entrypoint: app.main.handler
"""

import os
import shutil
import subprocess
import sys
import zipfile

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BACKEND_DIR, "build_lambda")
APP_SRC_DIR = os.path.join(BACKEND_DIR, "app")
REQ_FILE = os.path.join(BACKEND_DIR, "requirements-lambda.txt")
ZIP_OUTPUT = os.path.join(BACKEND_DIR, "lambda_package.zip")


def clean():
    """Remove previous build artifacts."""
    print("🧹 Cleaning previous build artifacts...")
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    if os.path.exists(ZIP_OUTPUT):
        os.remove(ZIP_OUTPUT)


def install_dependencies():
    """Install production dependencies targeted for Amazon Linux / Python 3.12."""
    print("📦 Installing Linux x86_64 dependencies for Python 3.12...")
    os.makedirs(BUILD_DIR, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--platform",
        "manylinux2014_x86_64",
        "--target",
        BUILD_DIR,
        "--only-binary=:all:",
        "--implementation",
        "cp",
        "--python-version",
        "3.12",
        "--upgrade",
        "-r",
        REQ_FILE,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ pip install failed:\n", result.stderr)
        sys.exit(1)
    print("✅ Dependencies installed successfully.")


def copy_application():
    """Copy the application code into the build package."""
    print("📂 Copying backend/app code...")
    dest_app = os.path.join(BUILD_DIR, "app")
    shutil.copytree(
        APP_SRC_DIR,
        dest_app,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"),
    )
    print("✅ Application copied.")


def create_zip():
    """Package the build directory into a deployment ZIP."""
    print(f"🗜️  Compressing into {os.path.basename(ZIP_OUTPUT)}...")
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BUILD_DIR):
            for file in files:
                if file.endswith((".pyc", ".pyo")):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, BUILD_DIR)
                zipf.write(file_path, arcname)

    size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print(f"🎉 Deployment package created successfully: {size_mb:.2f} MB")
    print(f"   Handler location: app.main.handler")


def cleanup_build():
    """Remove temporary build directory to conserve disk space."""
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    print("🧹 Temporary build directory cleaned.")


if __name__ == "__main__":
    clean()
    install_dependencies()
    copy_application()
    create_zip()
    cleanup_build()
