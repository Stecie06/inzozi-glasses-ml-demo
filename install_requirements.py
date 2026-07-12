import subprocess
import sys
import importlib

def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Successfully installed {package}")
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package}")

def check_package(package_name):
    try:
        importlib.import_module(package_name)
        print(f"✓ {package_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name} is not installed")
        return False

def main():
    print("Installing Smart Glasses System Requirements...")
    
    requirements = [
        "opencv-python",
        "face-recognition",
        "numpy", 
        "pyserial",
        "Pillow"
    ]
    
    # Install missing packages
    for package in requirements:
        if not check_package(package.split('-')[0]):  # Handle package names with hyphens
            install_package(package)
    
    print("\n Installation complete!")
    print("\nNext steps:")
    print("1. Upload the Arduino code to your Arduino board")
    print("2. Run: python smart_glasses_system.py")
    print("3. Make sure your webcam and Arduino are connected")

if __name__ == "__main__":
    main()