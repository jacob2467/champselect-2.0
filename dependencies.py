import importlib.util
import subprocess

package_names: list[str] = ["requests"]

def install_dependencies():
    """
    Ensure all package names listed in package_names are installed; install any that are missing.
    
    Iterates over package_names, skips packages that are already importable, and attempts to install missing packages using the system pip command.
    
    Raises:
        RuntimeError: If installation of a package fails.
    """
    for package in package_names:
        # Skip installing if the module is already installed
        if importlib.util.find_spec(package) is not None:
            print(f"Package '{package}' is already installed - skipping...\n")
            continue
        else:
            print(f"Package '{package}' not found - attempting to install...\n")

        try:
            subprocess.run(["pip3", "install", package])
        except Exception:
            try:
                subprocess.run(["pip", "install", package])
            except Exception as e:
                raise RuntimeError(f"Unable to install package '{package}' due to an error: {e}")
        print(f"\nSuccessfully installed package '{package}'!\n")

    if __name__ == "__main__":
        input("Press any key to continue...")