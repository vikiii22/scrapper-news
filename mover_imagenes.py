import os
import shutil

def move_images_to_root():
    """
    Recursively finds all image files in subdirectories of the target directory,
    moves them to the target directory itself, and removes the now-empty subdirectories.
    """
    # Use a raw string for the path to avoid issues with backslashes
    target_dir = r"C:\Users\joseantonio.sanchez\Pictures\amc"
    
    # Common image file extensions
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    # Ensure the target directory exists
    if not os.path.isdir(target_dir):
        print(f"Error: The directory was not found: {target_dir}")
        return

    print(f"Scanning for images in subdirectories of {target_dir}...")

    moved_files_count = 0
    # Walk through the directory tree, starting from the root
    for dirpath, dirnames, filenames in os.walk(target_dir):
        # Skip the root directory itself, we only want to process subdirectories
        if dirpath == target_dir:
            continue

        for filename in filenames:
            # Check if the file has a recognized image extension
            if os.path.splitext(filename)[1].lower() in image_extensions:
                source_path = os.path.join(dirpath, filename)
                dest_path = os.path.join(target_dir, filename)

                # Handle potential name conflicts in the destination
                counter = 1
                base, ext = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    dest_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
                    counter += 1
                
                try:
                    shutil.move(source_path, dest_path)
                    print(f"Moved: {source_path} -> {dest_path}")
                    moved_files_count += 1
                except Exception as e:
                    print(f"Error moving '{filename}': {e}")

    if moved_files_count > 0:
        print(f"\nMoved {moved_files_count} image files to the root directory.")
    else:
        print("\nNo image files were found in the subdirectories to move.")

    # --- Clean up empty subdirectories ---
    print("\nCleaning up empty directories...")
    cleaned_count = 0
    # Walk again, but this time from the bottom up to safely remove dirs
    for dirpath, dirnames, filenames in os.walk(target_dir, topdown=False):
        # Don't try to remove the root directory
        if dirpath == target_dir:
            continue
        
        # If the directory is empty, remove it
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
                print(f"Removed empty directory: {dirpath}")
                cleaned_count += 1
            except OSError as e:
                print(f"Error removing directory {dirpath}: {e}")

    if cleaned_count > 0:
        print(f"\nCleaned up {cleaned_count} empty directories.")
    else:
        print("No empty directories to clean up.")

    print("\nProcess completed.")

if __name__ == "__main__":
    move_images_to_root()
