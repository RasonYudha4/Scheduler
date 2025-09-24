import os
import time
import subprocess
import re
from datetime import datetime

def cleaner(name: str) -> str:
    """
    Clean folder name by:
      1. Removing leading number-dot-space pattern (e.g., '1. Folder' -> 'Folder')
      2. Removing everything starting from 'Eps' (case-insensitive)
      3. Replacing spaces with underscores
    """
    # Remove leading number-dot-space
    cleaned = re.sub(r'^\d+\.\s*', '', name)

    # Remove everything from 'Eps' onwards (case-insensitive)
    cleaned = re.sub(r'\s*Eps.*$', '', cleaned, flags=re.IGNORECASE)

    # Convert to Title Case (each word capitalized)
    cleaned = cleaned.title()

    # Replace spaces with underscores
    cleaned = cleaned.replace(" ", "_")

    return cleaned

def wait_until(target_hour, target_minute):
    """Pause execution until system time matches target hour:minute."""
    print(f"⏳ Waiting until {target_hour:02d}:{target_minute:02d} ...")
    while True:
        now = datetime.now().time()
        if now.hour == target_hour and now.minute == target_minute:
            print(f"✅ Time reached: {target_hour:02d}:{target_minute:02d}")
            return True
        time.sleep(1)

def should_stop_execution():
    """Check if current time is 08:00 or later, indicating we should stop."""
    now = datetime.now().time()
    # Stop if time is between 08:00 and 19:52 (before next start time)
    if now.hour >= 8 and now.hour < 19:
        return True
    elif now.hour == 19 and now.minute < 52:
        return True
    return False

def traverse_and_list_videos_in_film_folders(base_path, log_file_path):
    """Recursively traverse folders and log video files only from '1. Film' folders."""
    video_count = 0
    
    # Open log file in append mode to update for every found file
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"Movies Folder Search - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("=" * 60 + "\n\n")
        
        for root, dirs, files in os.walk(base_path):
            # Check if we should stop execution (time is 08:00 or later)
            if should_stop_execution():
                print(f"🛑 Stopping execution at {datetime.now().strftime('%H:%M:%S')} - reached 08:00 cutoff time")
                log_file.write(f"\nExecution stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - reached 08:00 cutoff time\n")
                return video_count
                
            # Check if current folder is named "1. Film"
            folder_name = os.path.basename(root)
            if folder_name == "1. Film":
                # Get the parent folder name (the folder containing "1. Film")
                parent_folder_path = os.path.dirname(root)
                raw_parent_folder_name = os.path.basename(parent_folder_path)
                parent_folder_name = cleaner(raw_parent_folder_name)
                
                for file in files:
                    # Check stop time before each file processing
                    if should_stop_execution():
                        print(f"🛑 Stopping execution at {datetime.now().strftime('%H:%M:%S')} - reached 08:00 cutoff time")
                        log_file.write(f"\nExecution stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - reached 08:00 cutoff time\n")
                        return video_count
                        
                    if not file.startswith("._") and file.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm")):
                        # Get file extension
                        file_name, file_extension = os.path.splitext(file)
                        
                        # Use parent folder name with underscores instead of original filename
                        file_with_underscores = parent_folder_name + file_extension
                        
                        log_entry = f"success {file_with_underscores}\n"
                        log_file.write(log_entry)
                        log_file.flush()  # Ensure immediate write to file
                        print(f"✅ Logged (Movies): {file} -> {file_with_underscores}")
                        
                        # Execute AWS S3 upload command
                        original_file_path = os.path.join(root, file)
                        s3_command = [
                            "aws", "s3", "cp", 
                            original_file_path, 
                            f"s3://vod-workflow-sg-source-224861044470/{file_with_underscores}"
                        ]
                        
                        try:
                            print(f"🚀 Uploading to S3: {file} as {file_with_underscores}")
                            result = subprocess.run(s3_command, capture_output=True, text=True, shell=False)
                            if result.returncode == 0:
                                print(f"✅ S3 Upload successful: {file_with_underscores}")
                            else:
                                print(f"❌ S3 Upload failed for {file}: {result.stderr}")
                        except FileNotFoundError:
                            print(f"❌ AWS CLI not found in PATH. Trying full path...")
                            # Try with full path as fallback
                            full_path_command = f'"C:\\Program Files\\Amazon\\AWSCLIV2\\aws.exe" s3 cp "{original_file_path}" s3://vod-workflow-sg-source-224861044470/{file_with_underscores}'
                            try:
                                result = subprocess.run(full_path_command, shell=True, capture_output=True, text=True)
                                if result.returncode == 0:
                                    print(f"✅ S3 Upload successful (full path): {file_with_underscores}")
                                else:
                                    print(f"❌ S3 Upload failed (full path) for {file}: {result.stderr}")
                            except Exception as e2:
                                print(f"❌ Error with full path AWS upload for {file}: {str(e2)}")
                        except Exception as e:
                            print(f"❌ Error executing S3 upload for {file}: {str(e)}")
                        
                        video_count += 1
        
        # Write summary for movies section
        log_file.write("\n" + "-" * 40 + "\n")
        log_file.write(f"Movies search completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Total video files found in movies: {video_count}\n\n")
    
    return video_count

def traverse_and_list_all_videos_in_series(base_path, log_file_path):
    """Recursively traverse series folder and log ALL video files found."""
    video_count = 0
    
    # Open log file in append mode
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"Series Folder Search - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("=" * 60 + "\n\n")
        
        for root, dirs, files in os.walk(base_path):
            # Check if we should stop execution (time is 08:00 or later)
            if should_stop_execution():
                print(f"🛑 Stopping execution at {datetime.now().strftime('%H:%M:%S')} - reached 08:00 cutoff time")
                log_file.write(f"\nExecution stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - reached 08:00 cutoff time\n")
                return video_count
                
            # Get current folder name and replace spaces with underscores
            folder_name = os.path.basename(root)
            folder_with_underscores = cleaner(folder_name)
            
            for file in files:
                # Check stop time before each file processing
                if should_stop_execution():
                    print(f"🛑 Stopping execution at {datetime.now().strftime('%H:%M:%S')} - reached 08:00 cutoff time")
                    log_file.write(f"\nExecution stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - reached 08:00 cutoff time\n")
                    return video_count
                    
                if not file.startswith("._") and file.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm")):
                    # Replace spaces with underscores for the log entry
                    file_with_underscores = cleaner(file)
                    log_entry = f"success {folder_with_underscores}/{file_with_underscores}\n"
                    log_file.write(log_entry)
                    log_file.flush()  # Ensure immediate write to file
                    print(f"✅ Logged (Series): {folder_name}/{file}")
                    
                    # Execute AWS S3 upload command
                    original_file_path = os.path.join(root, file)
                    s3_command = [
                        "aws", "s3", "cp", 
                        original_file_path, 
                        f"s3://vod-workflow-sg-source-224861044470/{folder_with_underscores}/{file_with_underscores}"
                    ]
                    
                    try:
                        print(f"🚀 Uploading to S3: {folder_name}/{file}")
                        result = subprocess.run(s3_command, capture_output=True, text=True, shell=False)
                        if result.returncode == 0:
                            print(f"✅ S3 Upload successful: {folder_with_underscores}/{file_with_underscores}")
                        else:
                            print(f"❌ S3 Upload failed for {file}: {result.stderr}")
                    except FileNotFoundError:
                        print(f"❌ AWS CLI not found in PATH. Trying full path...")
                        # Try with full path as fallback
                        full_path_command = f'"C:\\Program Files\\Amazon\\AWSCLIV2\\aws.exe" s3 cp "{original_file_path}" s3://vod-workflow-sg-source-224861044470/{folder_with_underscores}/{file_with_underscores}'
                        try:
                            result = subprocess.run(full_path_command, shell=True, capture_output=True, text=True)
                            if result.returncode == 0:
                                print(f"✅ S3 Upload successful (full path): {folder_with_underscores}/{file_with_underscores}")
                            else:
                                print(f"❌ S3 Upload failed (full path) for {file}: {result.stderr}")
                        except Exception as e2:
                            print(f"❌ Error with full path AWS upload for {file}: {str(e2)}")
                    except Exception as e:
                        print(f"❌ Error executing S3 upload for {file}: {str(e)}")
                    
                    video_count += 1
        
        # Write summary for series section
        log_file.write("\n" + "-" * 40 + "\n")
        log_file.write(f"Series search completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Total video files found in series: {video_count}\n\n")
    
    return video_count

if __name__ == "__main__":
    # Step 1: Change to E: drive
    try:
        os.chdir("E:/")
        print(f"✅ Changed to E: drive: {os.getcwd()}")
    except FileNotFoundError:
        print("❌ Drive E:/ not found!")
        exit(1)
    
    # Step 2: Change to movies folder
    try:
        os.chdir("movies")
        movies_path = os.getcwd()
        print(f"✅ Changed to movies folder: {movies_path}")
    except FileNotFoundError:
        print("❌ Movies folder not found in E:/")
        # Try alternative common names
        alt_names = ["Movies", "MOVIES", "movie", "Movie"]
        found = False
        for alt_name in alt_names:
            try:
                os.chdir(f"E:/{alt_name}")
                movies_path = os.getcwd()
                print(f"✅ Found movies folder as '{alt_name}': {movies_path}")
                found = True
                break
            except FileNotFoundError:
                continue
        
        if not found:
            print("❌ No movies folder found with common names!")
            exit(1)
    
    # Step 3: Wait until target time
    wait_until(21, 26)
    
    # Step 4: Create log file path in E: root (initialize with header)
    log_file_path = "E:/logs.txt"
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"Video Search Log - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("=" * 80 + "\n\n")
    
    # Step 5: Traverse movies folder and log video files only from "1. Film" folders
    print(f"\n=== Searching for video files in '1. Film' folders within {movies_path} ===")
    print(f"📝 Logging results to: {log_file_path}")
    total_movies = traverse_and_list_videos_in_film_folders(movies_path, log_file_path)
    
    print(f"\n✅ Finished movies search. Found {total_movies} video files in '1. Film' folders.")
    
    # Step 6: Change to series folder
    try:
        os.chdir("E:/series")
        series_path = os.getcwd()
        print(f"✅ Changed to series folder: {series_path}")
    except FileNotFoundError:
        print("❌ Series folder not found in E:/")
        # Try alternative common names
        alt_names = ["Series", "SERIES", "TV Shows", "TV_Shows", "Shows", "show"]
        found = False
        for alt_name in alt_names:
            try:
                os.chdir(f"E:/{alt_name}")
                series_path = os.getcwd()
                print(f"✅ Found series folder as '{alt_name}': {series_path}")
                found = True
                break
            except FileNotFoundError:
                continue
        
        if not found:
            print("❌ No series folder found with common names!")
            print(f"📋 Movies search completed. Log file saved at: {log_file_path}")
            exit(1)
    
    # Step 7: Traverse series folder and log ALL video files
    print(f"\n=== Searching for ALL video files within {series_path} ===")
    total_series = traverse_and_list_all_videos_in_series(series_path, log_file_path)
    
    print(f"\n✅ Finished series search. Found {total_series} video files in series folder.")
    
    # Final summary
    total_all = total_movies + total_series
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write("=" * 80 + "\n")
        log_file.write(f"FINAL SUMMARY - Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Total movies (from '1. Film' folders): {total_movies}\n")
        log_file.write(f"Total series (all video files): {total_series}\n")
        log_file.write(f"Grand total video files found: {total_all}\n")
    
    print(f"📋 Complete log file saved at: {log_file_path}")
    print(f"🎬 Grand total: {total_all} video files found ({total_movies} movies + {total_series} series)")