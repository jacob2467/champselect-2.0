import subprocess
import warnings

package_names: list[str] = ["requests", "flask", "flask-cors"]

for name in package_names:
    try:
        print(f"\nInstalling package '{name}'...\n")
        subprocess.run(["pip", "install", name])
    except Exception as e:
        warnings.warn(f"Unable to install {name} - trying pip3 instead of pip (works on some OSX installations)")
        try:
            subprocess.run(["pip", "install", name])
        except Exception as e:
            raise RuntimeError(f"Unable to install {name}: {e}")
    print(f"\nSuccessfully installed package '{name}'!\n")

input("Press any key to continue...")