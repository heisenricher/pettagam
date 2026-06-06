import os
import sys
import subprocess
from yt_dlp.postprocessor import PostProcessor

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

class CleanSubtitlesPP(PostProcessor):
    """Custom postprocessor to deduplicate rolling/overlapping subtitles
    so they display as a single clean line at a time.
    """
    def run(self, information):
        requested_subs = information.get('requested_subtitles', {})
        for lang_info in requested_subs.values():
            filepath = lang_info.get('filepath')
            if filepath and os.path.exists(filepath):
                self.clean_file(filepath)
        return [], information

    def clean_file(self, filepath):
        import re
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into blocks (cues)
            blocks = re.split(r'\n\s*\n', content)
            cleaned_blocks = []
            
            for block in blocks:
                lines = block.splitlines()
                if not lines:
                    continue
                
                # Keep header blocks as-is
                if any(lines[0].startswith(x) for x in ['WEBVTT', 'STYLE', 'NOTE', 'DEFAULTS']):
                    cleaned_blocks.append('\n'.join(lines))
                    continue
                
                # Find timestamp line
                time_idx = -1
                for idx, line in enumerate(lines):
                    if '-->' in line:
                        time_idx = idx
                        break
                        
                if time_idx == -1:
                    cleaned_blocks.append('\n'.join(lines))
                    continue
                    
                header_lines = lines[:time_idx + 1]
                text_lines = lines[time_idx + 1:]
                
                non_empty_text_lines = []
                for t_line in text_lines:
                    clean_text = re.sub(r'<[^>]+>', '', t_line).strip()
                    if clean_text:
                        non_empty_text_lines.append((t_line, clean_text))
                        
                if non_empty_text_lines:
                    # Keep only the last line of text to deduplicate rolling/overlapping lines
                    selected_line = non_empty_text_lines[-1][0]
                    cleaned_blocks.append('\n'.join(header_lines + [selected_line]))
                else:
                    cleaned_blocks.append('\n'.join(header_lines))
                    
            new_content = '\n\n'.join(cleaned_blocks)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"🧹 Cleaned up scrolling duplicates in subtitle: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"⚠️ Error cleaning subtitle file {filepath}: {e}")

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
    print("🎥 YOUTUBE VIDEO & AUDIO DOWNLOADER")
    print("="*60)
    print(f"📁 Default download directory: {DOWNLOAD_DIR}")
    print("="*60)

    if HAS_FFMPEG:
        print("✅ ffmpeg is INSTALLED! High-res merging & subtitle embedding are supported.")
    else:
        print("⚠️ ffmpeg is NOT INSTALLED/FOUND.")
        print("   Without ffmpeg, high-resolution formats will download video-only, or fallback to 720p pre-merged.")
        print("   To install ffmpeg on Windows:")
        print("     Run: winget install Gyan.FFmpeg")
    print("="*60)

    # Input video URL
    video_url = input("\n🔗 Enter YouTube Video URL: ").strip()

    if not video_url:
        print("❌ Error: You must enter a valid YouTube URL.")
        input("\nPress Enter to exit...")
        return

    print("\n🔍 Fetching video details and format options...")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    sorted_video_formats = []
    subtitles = {}
    auto_subtitles = {}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            
            title = info_dict.get('title', 'Unknown Title')
            duration = info_dict.get('duration', 0)
            uploader = info_dict.get('uploader', 'Unknown')
            
            # Format duration
            mins, secs = divmod(duration, 60)
            hours, mins = divmod(mins, 60)
            duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
            
            print("\n" + "="*50)
            print("🎬 VIDEO METADATA")
            print("="*50)
            print(f"Title:    {title}")
            print(f"Channel:  {uploader}")
            print(f"Duration: {duration_str}")
            print("="*50)
            
            # Find all available resolutions, grouped by height and framerate
            formats = info_dict.get('formats', [])
            unique_formats = {}
            for f in formats:
                if f.get('vcodec') == 'none':
                    continue
                height = f.get('height')
                if not height:
                    continue
                fps = f.get('fps')
                note = f.get('format_note', '')
                
                fps_str = f" {int(fps)}fps" if fps and fps > 1 else ""
                hdr_str = " HDR" if note and "HDR" in note.upper() else ""
                label = f"{height}p{fps_str}{hdr_str}"
                
                tbr = f.get('tbr') or 0
                if label not in unique_formats or tbr > unique_formats[label]['tbr']:
                    unique_formats[label] = {
                        'height': height,
                        'fps': fps,
                        'tbr': tbr,
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext')
                    }
            
            # Sort unique formats by height, then fps, then bitrate
            def sort_key(item):
                _, info = item
                h = info['height'] or 0
                fps_val = info['fps'] or 0
                tbr_val = info['tbr'] or 0
                return (h, fps_val, tbr_val)
                
            sorted_video_formats = sorted(unique_formats.items(), key=sort_key, reverse=True)
            
            # Extract subtitles
            subtitles = info_dict.get('subtitles', {})
            auto_subtitles = info_dict.get('automatic_captions', {})
            
            print("\n📝 SUBTITLE INFO")
            if subtitles or auto_subtitles:
                total_subs = len(subtitles) + len(auto_subtitles)
                print(f"Subtitles found: {total_subs} language option(s) available.")
            else:
                print("No subtitles available for this video.")
            print("="*50)
            
    except Exception as e:
        print(f"❌ Error fetching metadata: {e}")
        input("\nPress Enter to exit...")
        return

    if not sorted_video_formats:
        print("❌ Error: Could not find any valid video streams.")
        input("\nPress Enter to exit...")
        return

    print("\nAvailable Download Options:")
    options = []
    options.append(("Best Video Quality + High Quality Audio", "best", None))
    
    for label, info in sorted_video_formats:
        options.append((f"Video - {label}", "video_format", info['format_id']))
        
    options.append(("Audio Only (High Resolution MP3/M4A)", "audio", None))
    
    for idx, opt in enumerate(options, 1):
        print(f"[{idx}] {opt[0]}")
        
    print("-" * 50)
    
    while True:
        try:
            choice = int(input(f"Select choice (1-{len(options)}): "))
            if 1 <= choice <= len(options):
                selected_option = options[choice - 1]
                break
            else:
                print(f"Invalid option. Enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Please enter a valid number.")
            
    label, opt_type, format_id = selected_option
    print(f"\n✅ Selected format: {label}")

    # Subtitle selection logic
    chosen_sub_lang = None
    sub_type = None
    
    if opt_type != 'audio':
        sub_options = []
        if subtitles:
            for lang in subtitles.keys():
                sub_options.append((f"{lang} [Manual]", lang, 'manual'))
        if auto_subtitles:
            for lang in auto_subtitles.keys():
                if not any(opt[1] == lang for opt in sub_options):
                    sub_options.append((f"{lang} [Auto-generated]", lang, 'automatic'))
                    
        if sub_options:
            print("\nAvailable Subtitles:")
            print("[1] Do not download subtitles")
            for idx, (lbl, lang, s_type) in enumerate(sub_options, 2):
                print(f"[{idx}] {lbl}")
            print("-" * 50)
            
            while True:
                try:
                    sub_choice = int(input(f"Select subtitle option (1-{len(sub_options) + 1}): "))
                    if 1 <= sub_choice <= len(sub_options) + 1:
                        if sub_choice == 1:
                            chosen_sub_lang = None
                            sub_type = None
                        else:
                            selected_sub = sub_options[sub_choice - 2]
                            chosen_sub_lang = selected_sub[1]
                            sub_type = selected_sub[2]
                        break
                    else:
                        print(f"Invalid option. Enter a number between 1 and {len(sub_options) + 1}.")
                except ValueError:
                    print("Please enter a valid number.")
            
            if chosen_sub_lang:
                print(f"\n✅ Selected subtitle language: {chosen_sub_lang} ({sub_type})")
            else:
                print("\n✅ Selected: No subtitles")
        else:
            print("\n📝 No subtitles available for this video.")
    else:
        print("\n🎵 Audio Only selected. Skipping subtitles.")

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()
            sys.stdout.write(f"\rDownloading: {percent} | Speed: {speed} | ETA: {eta}   ")
            sys.stdout.flush()
        elif d['status'] == 'finished':
            sys.stdout.write("\nDownload complete! Merging/Post-processing...\n")
            sys.stdout.flush()

    download_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
    }
    
    if opt_type == 'audio':
        download_opts['format'] = 'bestaudio/best'
        if HAS_FFMPEG:
            download_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
            print("🎵 Format: High-Resolution Audio (converting to 320kbps MP3)")
        else:
            print("🎵 Format: Best Audio (raw file download since ffmpeg is missing)")
            
    elif opt_type == 'best':
        if HAS_FFMPEG:
            download_opts['format'] = 'bestvideo+bestaudio/best'
            print("🎬 Format: Best Video + Best Audio (merged)")
        else:
            download_opts['format'] = 'best'
            print("🎬 Format: Best Pre-merged Stream (since ffmpeg is missing)")
            
    elif opt_type == 'video_format':
        if HAS_FFMPEG:
            download_opts['format'] = f"{format_id}+bestaudio/best"
            print(f"🎬 Format: Selected Video Stream ({label}) + High-Quality Audio (merged)")
        else:
            download_opts['format'] = format_id
            print(f"🎬 Format: Selected Video Stream ({label}) (direct download, no audio merging since ffmpeg is missing)")
            
    if chosen_sub_lang and opt_type != 'audio':
        download_opts['writesubtitles'] = True
        if sub_type == 'automatic':
            download_opts['writeautomaticsub'] = True
        download_opts['subtitleslangs'] = [chosen_sub_lang]
        
        if HAS_FFMPEG:
            download_opts['postprocessors'] = download_opts.get('postprocessors', []) + [{
                'key': 'FFmpegEmbedSubtitle',
                'already_have_subtitle': False,
            }]
            download_opts['merge_output_format'] = 'mkv'
            print(f"📝 Subtitles: Language '{chosen_sub_lang}' will be embedded in output video.")
        else:
            print(f"📝 Subtitles: Language '{chosen_sub_lang}' will download as a separate file next to video.")
            
    print(f"\n🚀 Downloading to: {DOWNLOAD_DIR}...\n")
    
    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.add_post_processor(CleanSubtitlesPP(), when='post_process')
            pp_list = ydl._pps.get('post_process', [])
            if pp_list:
                custom_pp = pp_list.pop()
                pp_list.insert(0, custom_pp)
                
            ydl.download([video_url])
        print("\n🎉 SUCCESS! Download complete.")
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        
    input("\nPress Enter to exit...")

if __name__ == '__main__':
    main()
