import importlib.util
import subprocess

package_names: list[str] = ["requests"]

def install_dependencies():
    for package in package_names:
        # Skip installing if the module is already installed
        if importlib.util.find_spec(package) is None:
            continue

        try:
            print(f"\nInstalling package '{package}'...\n")
            subprocess.run(["pip3", "install", package])
        except Exception:
            try:
                subprocess.run(["pip", "install", package])
            except Exception as e:
                raise RuntimeError(f"Unable to install package '{package}' due to an error: {e}")
        print(f"\nSuccessfully installed package '{package}'!\n")

    if __name__ == "__main__":
        input("Press any key to continue...")