"""
🎵 YouTube Music Downloader with GUI
Complete solution for downloading audio/playlists with metadata
"""

# ========== INSTALLATION & SETUP ==========
print("🔄 Installing required packages...")
!pip install yt-dlp pydrive mutagen -q

import os
import re
import json
import threading
from pathlib import Path
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from google.colab import drive
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TCON, APIC

# ========== CONFIGURATION ==========
class Config:
    DEFAULT_DRIVE_FOLDER = "YouTube Music Downloads"
    SUPPORTED_FORMATS = ['mp3', 'm4a', 'flac', 'opus', 'wav']
    DEFAULT_FORMAT = 'mp3'
    DEFAULT_QUALITY = '192'

config = Config()

# ========== GUI COMPONENTS ==========
class MusicDownloaderGUI:
    def __init__(self):
        self.setup_ui()
        
    def setup_ui(self):
        # URL Input
        self.url_input = widgets.Textarea(
            value='',
            placeholder='Enter YouTube URL or playlist URL (one per line for multiple)',
            description='URL(s):',
            layout=widgets.Layout(width='90%', height='80px'),
            disabled=False
        )
        
        # Download Type
        self.download_type = widgets.RadioButtons(
            options=['Single Video', 'Entire Playlist'],
            value='Single Video',
            description='Type:',
            disabled=False
        )
        
        # Save Location
        self.save_location = widgets.RadioButtons(
            options=['Google Drive', 'Local (Temporary)'],
            value='Google Drive',
            description='Save to:',
            disabled=False
        )
        
        # Folder Name
        self.folder_input = widgets.Text(
            value=config.DEFAULT_DRIVE_FOLDER,
            placeholder='Folder name in Google Drive',
            description='Folder:',
            disabled=False,
            layout=widgets.Layout(width='300px')
        )
        
        # Audio Format
        self.format_dropdown = widgets.Dropdown(
            options=config.SUPPORTED_FORMATS,
            value=config.DEFAULT_FORMAT,
            description='Format:',
            disabled=False
        )
        
        # Audio Quality
        self.quality_input = widgets.IntText(
            value=192,
            description='Quality (kbps):',
            disabled=False,
            min=64,
            max=320
        )
        
        # Metadata Options
        self.metadata_checkbox = widgets.Checkbox(
            value=True,
            description='Add metadata from YouTube',
            disabled=False,
            indent=False
        )
        
        # Thumbnail checkbox
        self.thumbnail_checkbox = widgets.Checkbox(
            value=True,
            description='Embed thumbnail',
            disabled=False,
            indent=False
        )
        
        # Progress Output
        self.progress_output = widgets.Output()
        
        # Status Label
        self.status_label = widgets.Label(value="Ready")
        
        # Download Button
        self.download_button = widgets.Button(
            description='🎵 Start Download',
            button_style='success',
            icon='download',
            layout=widgets.Layout(width='200px', height='50px')
        )
        self.download_button.on_click(self.on_download_clicked)
        
        # Clear Button
        self.clear_button = widgets.Button(
            description='Clear',
            button_style='',
            layout=widgets.Layout(width='100px', height='30px')
        )
        self.clear_button.on_click(self.on_clear_clicked)
        
        # Create UI Layout
        self.ui = widgets.VBox([
            widgets.HTML("<h2>🎵 YouTube Music Downloader</h2>"),
            widgets.HBox([
                widgets.VBox([
                    self.url_input,
                    self.download_type,
                    self.save_location,
                    self.folder_input,
                ]),
                widgets.VBox([
                    self.format_dropdown,
                    self.quality_input,
                    self.metadata_checkbox,
                    self.thumbnail_checkbox,
                ])
            ]),
            widgets.HTML("<hr>"),
            widgets.HBox([self.download_button, self.clear_button]),
            widgets.HTML("<hr>"),
            widgets.HTML("<h4>Progress:</h4>"),
            self.status_label,
            self.progress_output
        ])
    
    def display(self):
        display(self.ui)
    
    def update_status(self, message, level="info"):
        """Update status with colored message"""
        colors = {
            "info": "blue",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        color = colors.get(level, "black")
        self.status_label.value = f'<span style="color:{color}">{message}</span>'
    
    def log_progress(self, message, clear=False):
        """Add message to progress output"""
        with self.progress_output:
            if clear:
                clear_output()
            print(message)
    
    def on_download_clicked(self, b):
        """Handle download button click"""
        urls = self.url_input.value.strip()
        if not urls:
            self.update_status("❌ Please enter a URL", "error")
            return
        
        # Start download in separate thread
        thread = threading.Thread(target=self.start_download, args=(urls,))
        thread.start()
    
    def on_clear_clicked(self, b):
        """Clear all inputs"""
        self.url_input.value = ''
        with self.progress_output:
            clear_output()
        self.update_status("Cleared", "info")
    
    def start_download(self, urls):
        """Main download function"""
        try:
            self.update_status("⏳ Starting download...", "info")
            self.log_progress("=" * 60, clear=True)
            
            # Prepare download options
            urls_list = urls.split('\n')
            
            # Mount Google Drive if needed
            drive_path = None
            if self.save_location.value == 'Google Drive':
                self.log_progress("📁 Mounting Google Drive...")
                drive.mount('/content/drive')
                drive_base = '/content/drive/MyDrive'
                drive_path = os.path.join(drive_base, self.folder_input.value)
                os.makedirs(drive_path, exist_ok=True)
                self.log_progress(f"✅ Drive ready: {drive_path}")
            else:
                drive_path = '/content/downloads'
                os.makedirs(drive_path, exist_ok=True)
                self.log_progress(f"⚠️ Saving locally (temporary): {drive_path}")
            
            # Configure yt-dlp
            ydl_opts = self.get_ydl_options(drive_path)
            
            # Download
            if self.download_type.value == 'Entire Playlist':
                self.download_playlist(urls_list[0], ydl_opts, drive_path)
            else:
                self.download_videos(urls_list, ydl_opts, drive_path)
            
            self.update_status("✅ Download complete!", "success")
            
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}", "error")
            self.log_progress(f"Error details: {e}")
    
    def get_ydl_options(self, output_path):
        """Configure yt-dlp options"""
        format_map = {
            'mp3': 'bestaudio/best',
            'm4a': 'm4a/bestaudio/best',
            'flac': 'bestaudio[ext=flac]/bestaudio/best',
            'opus': 'bestaudio[ext=opus]/bestaudio/best',
            'wav': 'bestaudio[ext=wav]/bestaudio/best'
        }
        
        format_code = format_map.get(self.format_dropdown.value, 'bestaudio/best')
        
        return {
            'format': format_code,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.format_dropdown.value,
                'preferredquality': str(self.quality_input.value),
            }],
            'quiet': True,  # Less verbose output
            'no_warnings': True,
            'extract_flat': False,
            'progress_hooks': [self.progress_hook],
        }
    
    def progress_hook(self, d):
        """Handle download progress updates"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', '').strip()
            eta = d.get('_eta_str', '').strip()
            
            if percent != '0%':
                self.log_progress(f"⏬ {percent} complete | Speed: {speed} | ETA: {eta}")
        
        elif d['status'] == 'finished':
            filename = d.get('filename', 'Unknown')
            self.log_progress(f"✅ Downloaded: {os.path.basename(filename)}")
    
    def download_videos(self, urls, ydl_opts, output_path):
        """Download individual videos"""
        self.log_progress(f"📥 Downloading {len(urls)} video(s)...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(urls):
                if not url.strip():
                    continue
                
                self.log_progress(f"\n[{i+1}/{len(urls)}] Processing...")
                try:
                    info = ydl.extract_info(url.strip(), download=True)
                    
                    # Process metadata if requested
                    if self.metadata_checkbox.value:
                        self.add_metadata(info, output_path)
                    
                    self.log_progress(f"✓ Completed: {info.get('title', 'Unknown')}")
                    
                except Exception as e:
                    self.log_progress(f"✗ Failed: {url} - {str(e)}")
    
    def download_playlist(self, playlist_url, ydl_opts, output_path):
        """Download entire playlist"""
        self.log_progress(f"📚 Downloading playlist...")
        
        # Modify options for playlist
        playlist_opts = ydl_opts.copy()
        playlist_opts.update({
            'outtmpl': os.path.join(output_path, '%(playlist)s', '%(title)s.%(ext)s'),
            'quiet': True,
        })
        
        with yt_dlp.YoutubeDL(playlist_opts) as ydl:
            try:
                info = ydl.extract_info(playlist_url, download=True)
                
                # Process metadata for all downloaded files
                if self.metadata_checkbox.value and 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            self.add_metadata(entry, output_path)
                
                self.log_progress(f"✓ Playlist complete: {info.get('title', 'Unknown')}")
                self.log_progress(f"📊 Total: {info.get('playlist_count', '?')} tracks")
                
            except Exception as e:
                self.log_progress(f"✗ Playlist error: {str(e)}")
    
    def add_metadata(self, info, output_path):
        """Add ID3 metadata to audio files"""
        try:
            # Find the downloaded file
            filename = info.get('title', 'Unknown')
            file_ext = '.' + self.format_dropdown.value
            
            # Try different possible filenames
            possible_files = [
                os.path.join(output_path, f"{filename}{file_ext}"),
                os.path.join(output_path, f"{sanitize_filename(filename)}{file_ext}"),
            ]
            
            # For playlists
            if 'playlist' in info:
                playlist_folder = sanitize_filename(info.get('playlist', 'Playlist'))
                possible_files.append(
                    os.path.join(output_path, playlist_folder, f"{filename}{file_ext}")
                )
            
            audio_file = None
            for f in possible_files:
                if os.path.exists(f):
                    audio_file = f
                    break
            
            if not audio_file:
                return
            
            # Skip if not MP3 (EasyID3 only works with MP3)
            if self.format_dropdown.value != 'mp3':
                return
            
            # Add metadata using mutagen
            try:
                audio = EasyID3(audio_file)
            except:
                audio = EasyID3()
                audio.save(audio_file)
                audio = EasyID3(audio_file)
            
            # Set basic metadata
            if info.get('title'):
                audio['title'] = info['title']
            if info.get('artist') or info.get('uploader'):
                artist = info.get('artist') or info.get('uploader', 'Unknown')
                audio['artist'] = artist
            if info.get('album'):
                audio['album'] = info['album']
            elif info.get('playlist'):
                audio['album'] = info['playlist']
            if info.get('release_year'):
                audio['date'] = str(info['release_year'])
            elif info.get('upload_date'):
                audio['date'] = info['upload_date'][:4]
            
            # Track number for playlists
            if info.get('playlist_index'):
                audio['tracknumber'] = str(info['playlist_index'])
            
            audio.save()
            
            # Embed thumbnail if requested
            if self.thumbnail_checkbox.value and info.get('thumbnail'):
                self.embed_thumbnail(audio_file, info['thumbnail'])
            
        except Exception as e:
            # Silently fail on metadata errors
            pass
    
    def embed_thumbnail(self, audio_file, thumbnail_url):
        """Download and embed thumbnail in audio file"""
        try:
            import requests
            from io import BytesIO
            
            # Download thumbnail
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                # Load ID3 tags
                audio = ID3(audio_file)
                
                # Add APIC frame (album art)
                audio['APIC'] = APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,  # 3 is for cover image
                    desc='Cover',
                    data=response.content
                )
                
                audio.save()
                
        except:
            # Silently fail on thumbnail errors
            pass

# ========== UTILITY FUNCTIONS ==========
def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized = re.sub(r'[^\x00-\x7F]+', '', sanitized)
    return sanitized.strip()

def validate_url(url):
    """Validate YouTube URLs"""
    patterns = [
        r'(https?://)?(www\.)?(youtube|youtu)\.(com|be)/',
        r'(https?://)?music\.youtube\.com/'
    ]
    return any(re.match(pattern, url) for pattern in patterns)

# ========== MAIN EXECUTION ==========
def main():
    """Main function to run the GUI"""
    print("=" * 70)
    print("🎵 YOUTUBE MUSIC DOWNLOADER")
    print("=" * 70)
    print("Features:")
    print("• GUI interface for easy use")
    print("• Single videos & entire playlists")
    print("• Google Drive or local storage")
    print("• Multiple audio formats (MP3, M4A, FLAC, etc.)")
    print("• Metadata embedding (artist, album, thumbnail)")
    print("• Clean, minimal output")
    print("=" * 70)
    print()
    
    # Display the GUI
    gui = MusicDownloaderGUI()
    gui.display()
    
    # Instructions
    print("\n📋 Instructions:")
    print("1. Enter YouTube URL(s) in the box above")
    print("2. Choose download type (single or playlist)")
    print("3. Select save location (Drive recommended)")
    print("4. Configure format/quality if needed")
    print("5. Click 'Start Download'")
    print("6. For Google Drive: Authorize when prompted")
    
    return gui

# Run the application
if __name__ == "__main__":
    gui = main()
