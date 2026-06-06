import os
import sys
import subprocess

# Auto-install/check yt-dlp
try:
    import yt_dlp
except ImportError:
    print("yt-dlp is not installed. Installing it now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        import yt_dlp
        print("yt-dlp installed successfully!\n")
    except Exception as e:
        print(f"Failed to auto-install yt-dlp: {e}")
        print("Please run 'pip install yt-dlp' manually in your console.")
        input("\nPress Enter to exit...")
        sys.exit(1)

def get_download_path():
    """Returns the default downloads path for the current user."""
    if os.name == 'nt':
        import winreg
        try:
            sub_key = r'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                return winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        except Exception:
            return os.path.join(os.path.expanduser('~'), 'Downloads')
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')

def check_ffmpeg():
    """Checks if ffmpeg is available in the system path."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def main():
    DOWNLOAD_DIR = get_download_path()
    HAS_FFMPEG = check_ffmpeg()

    print("="*60)
    print("🎵 YOUTUBE AUDIO DOWNLOADER (Playlist & Video Support)")
    print("="*60)
    print(f"📁 Default download directory: {DOWNLOAD_DIR}")
    print("="*60)

    if HAS_FFMPEG:
        print("✅ ffmpeg is INSTALLED! Audio will be extracted to high-quality 320kbps MP3.")
    else:
        print("⚠️ ffmpeg is NOT INSTALLED/FOUND.")
        print("   Without ffmpeg, raw audio streams (e.g. .m4a or .webm) will be downloaded directly.")
        print("   To install ffmpeg on Windows:")
        print("     Run: winget install Gyan.FFmpeg")
    print("="*60)

    # Input YouTube URL
    video_url = input("\n🔗 Enter YouTube URL (Video or Playlist): ").strip()

    if not video_url:
        print("❌ Error: You must enter a valid YouTube URL.")
        input("\nPress Enter to exit...")
        return

    print("\n🔍 Analyzing link... Please wait.")
    
    # Configure flat extraction for quick link analysis
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            
            title = info_dict.get('title', 'Unknown Title')
            is_playlist = 'entries' in info_dict or info_dict.get('_type') == 'playlist'
            
            print("\n" + "="*50)
            print("🎬 METADATA & TYPE DETECTED")
            print("="*50)
            if is_playlist:
                entries_list = list(info_dict.get('entries', []))
                track_count = len(entries_list)
                print(f"Type:         Playlist 📁")
                print(f"Name:         {title}")
                print(f"Total Tracks: {track_count}")
            else:
                uploader = info_dict.get('uploader', 'Unknown')
                duration = info_dict.get('duration', 0)
                mins, secs = divmod(duration, 60)
                hours, mins = divmod(mins, 60)
                duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
                
                print(f"Type:         Single Video 🎬")
                print(f"Title:        {title}")
                print(f"Channel:      {uploader}")
                print(f"Duration:     {duration_str}")
            print("="*50)
            
    except Exception as e:
        print(f"❌ Error analyzing link: {e}")
        input("\nPress Enter to exit...")
        return

    # Confirm download start
    confirm = input("\nStart downloading audio? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '']:
        print("Download cancelled.")
        input("\nPress Enter to exit...")
        return

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()
            sys.stdout.write(f"\rDownloading: {percent} | Speed: {speed} | ETA: {eta}   ")
            sys.stdout.flush()
        elif d['status'] == 'finished':
            sys.stdout.write("\nDownload complete! Post-processing/Extracting audio...\n")
            sys.stdout.flush()

    download_opts = {
        'format': 'bestaudio/best',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
    }
    
    # Configure output directory
    if is_playlist:
        safe_title = "".join(x for x in title if x.isalnum() or x in " -_()")
        playlist_dir = os.path.join(DOWNLOAD_DIR, safe_title)
        download_opts['outtmpl'] = os.path.join(playlist_dir, '%(playlist_index)s - %(title)s.%(ext)s')
        print(f"\n📥 Playlist tracks will be saved in subfolder: {playlist_dir}")
    else:
        download_opts['outtmpl'] = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
        print(f"\n📥 Audio track will be saved directly to: {DOWNLOAD_DIR}")
        
    # Configure high quality MP3 extractor post-processor if ffmpeg is available
    if HAS_FFMPEG:
        download_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]
        print("🎵 Extracting: Converting to high-quality 320kbps MP3")
    else:
        print("🎵 Extracting: Keeping raw best quality audio stream directly (ffmpeg missing)")
        
    print(f"\n🚀 Starting download...\n")
    
    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([video_url])
        print("\n🎉 SUCCESS! All audio downloads completed successfully.")
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        
    input("\nPress Enter to exit...")

if __name__ == '__main__':
    main()
