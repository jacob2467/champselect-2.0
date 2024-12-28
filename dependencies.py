import subprocess
import sys
import importlib

def install_and_import(package):
    try:
        # If the package is already installed, just return it
        return importlib.import_module(package)
    except ModuleNotFoundError:
        print(f"Please wait, installing package \"{package}\"...")
        # Install the package with pip
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package],
            # Suppress pip output
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        # Return the installed package
        module = importlib.import_module(package)
        print(f"Successfully installed package \"{package}\"!")
        return module
    except Exception as e:
        print(f"Error while installing {package}: {e}")