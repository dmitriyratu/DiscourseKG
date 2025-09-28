import os
import site


def add_project_root_to_site_packages():
    """
    Automatically add the project root directory to Python's site-packages
    using a .pth file.
    """
    # Get the project root (parent of scripts directory)
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(scripts_dir)

    # Locate the user's site-packages directory
    site_packages_dir = site.getusersitepackages()

    # Ensure the site-packages directory exists
    os.makedirs(site_packages_dir, exist_ok=True)

    # Define the .pth file path
    pth_file = os.path.join(site_packages_dir, "current_project.pth")

    # Write the project root path to the .pth file
    try:
        with open(pth_file, "w") as f:
            f.write(project_root + "\n")
        print(f"Successfully added {project_root} to {pth_file}")
        print("✅ Now you can import from src/ from anywhere!")
    except Exception as e:
        print(f"Failed to create .pth file: {e}")


# Example usage
if __name__ == "__main__":
    add_project_root_to_site_packages()
