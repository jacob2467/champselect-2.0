import importlib.util
import subprocess

package_names: list[str] = ["requests", "flask", "flask-cors"]

def install_dependencies():
    for package in package_names:
        # Skip installing if the module is already installed
        if importlib.util.find_spec(package) is not None:
            print(f"Package '{package}' is already installed - skipping...\n")
            continue
        else:
            print(f"Package '{package}' not found - attempting to install...\n")

        try:
            subprocess.run(["pip3", "install", package], check=True)
        except Exception:
            try:
                subprocess.run(["pip", "install", package], check=True)
            except Exception as e:
                raise RuntimeError(f"Unable to install package '{package}' due to an error: {e}")
        print(f"\nSuccessfully installed package '{package}'!\n")

if __name__ == "__main__":
    install_dependencies()
    input("Press any key to continue...")