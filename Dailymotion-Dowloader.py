"""
🎬 Dailymotion Movie Downloader for Google Colab
Downloads movies from Dailymotion and saves to Google Drive
"""

# ========== INSTALLATION ==========
print("🎬 Installing Dailymotion downloader dependencies...")
!pip install yt-dlp pydrive requests beautifulsoup4 -q
!apt-get install -y ffmpeg > /dev/null 2>&1

import os
import re
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from google.colab import drive, files
import requests
from bs4 import BeautifulSoup
import yt_dlp
import warnings
warnings.filterwarnings('ignore')

# ========== DAILYMOTION HANDLER ==========
class DailymotionDownloader:
    """Handles Dailymotion video downloading"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_video_info(self, url):
        """Extract video information from Dailymotion URL"""
        try:
            print(f"🔍 Extracting video info from: {url}")
            
            # Use yt-dlp to get video info
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    print("❌ Could not extract video information")
                    return None
                
                # Extract available formats
                formats = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('vcodec') != 'none':  # Only video formats
                            quality = fmt.get('format_note', 'Unknown')
                            if not quality or quality == 'none':
                                height = fmt.get('height')
                                if height:
                                    quality = f"{height}p"
                                else:
                                    quality = 'Unknown'
                            
                            formats.append({
                                'format_id': fmt.get('format_id'),
                                'quality': quality,
                                'ext': fmt.get('ext', 'mp4'),
                                'filesize': fmt.get('filesize'),
                                'url': fmt.get('url'),
                            })
                
                # Get best thumbnail
                thumbnail = None
                if 'thumbnail' in info:
                    thumbnail = info['thumbnail']
                elif 'thumbnails' in info and info['thumbnails']:
                    thumbnail = info['thumbnails'][-1]['url']  # Last is usually highest quality
                
                video_info = {
                    'id': info.get('id', ''),
                    'title': info.get('title', 'Unknown Title'),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'thumbnail': thumbnail,
                    'formats': formats,
                    'webpage_url': info.get('webpage_url', url),
                }
                
                return video_info
                
        except Exception as e:
            print(f"❌ Error extracting video info: {str(e)}")
            return None
    
    def get_available_qualities(self, url):
        """Get list of available video qualities"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'listformats': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                qualities = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('vcodec') != 'none':  # Video formats only
                            quality = fmt.get('format_note', 'Unknown')
                            if not quality or quality == 'none':
                                height = fmt.get('height')
                                if height:
                                    quality = f"{height}p"
                                else:
                                    quality = 'Unknown'
                            
                            filesize = fmt.get('filesize')
                            size_str = f" ({self.format_size(filesize)})" if filesize else ""
                            
                            qualities.append({
                                'id': fmt.get('format_id'),
                                'quality': quality,
                                'display': f"{quality}{size_str}",
                                'ext': fmt.get('ext', 'mp4'),
                            })
                
                # Remove duplicates and sort
                seen = set()
                unique_qualities = []
                for q in qualities:
                    key = q['quality']
                    if key not in seen:
                        seen.add(key)
                        unique_qualities.append(q)
                
                # Sort by quality (highest first)
                def quality_sort(q):
                    match = re.search(r'(\d+)', q['quality'])
                    return int(match.group(1)) if match else 0
                
                unique_qualities.sort(key=quality_sort, reverse=True)
                
                return unique_qualities
                
        except Exception as e:
            print(f"❌ Error getting qualities: {str(e)}")
            return []
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        if not size_bytes:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def download_video(self, url, quality='best', output_path='.', output_filename=None, progress_callback=None):
        """Download video with specified quality"""
        try:
            print(f"⬇️ Downloading video from: {url}")
            
            # Prepare download options
            if quality == 'best':
                format_spec = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == 'worst':
                format_spec = 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst'
            else:
                # Try to match quality
                format_spec = f'bestvideo[height<={quality.replace("p", "")}]+bestaudio/best[height<={quality.replace("p", "")}]'
            
            # Create output template
            if output_filename:
                outtmpl = os.path.join(output_path, output_filename)
            else:
                outtmpl = os.path.join(output_path, '%(title)s.%(ext)s')
            
            ydl_opts = {
                'format': format_spec,
                'outtmpl': outtmpl,
                'merge_output_format': 'mp4',
                'quiet': False,
                'no_warnings': False,
                'progress_hooks': [progress_callback] if progress_callback else [],
                'postprocessor_args': ['-c', 'copy'],  # Try to copy without re-encoding
                'retries': 10,
                'fragment_retries': 10,
                'skip_unavailable_fragments': True,
                'continuedl': True,
            }
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Get final file path (after post-processing)
                final_filename = filename
                if filename.endswith('.webm'):
                    final_filename = filename.replace('.webm', '.mp4')
                elif filename.endswith('.part'):
                    final_filename = filename.replace('.part', '.mp4')
                
                return True, final_filename, info
                
        except Exception as e:
            print(f"❌ Download error: {str(e)}")
            return False, None, None

# ========== GOOGLE DRIVE INTEGRATION ==========
class GoogleDriveManager:
    """Manages Google Drive operations"""
    
    def __init__(self):
        self.drive_mounted = False
        self.base_path = '/content/drive/MyDrive'
    
    def mount_drive(self):
        """Mount Google Drive"""
        try:
            if not self.drive_mounted:
                print("📁 Mounting Google Drive...")
                drive.mount('/content/drive')
                self.drive_mounted = True
                print("✅ Google Drive mounted successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to mount Google Drive: {str(e)}")
            return False
    
    def create_drive_folder(self, folder_name):
        """Create a folder in Google Drive"""
        try:
            self.mount_drive()
            
            # Create folder path
            folder_path = os.path.join(self.base_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            print(f"📂 Created folder: {folder_path}")
            return folder_path
            
        except Exception as e:
            print(f"❌ Failed to create folder: {str(e)}")
            return None
    
    def save_to_drive(self, file_path, drive_folder='Dailymotion Downloads'):
        """Save file to Google Drive"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ File doesn't exist: {file_path}")
                return None
            
            # Create Drive folder
            drive_path = self.create_drive_folder(drive_folder)
            if not drive_path:
                return None
            
            # Copy file to Drive
            filename = os.path.basename(file_path)
            destination = os.path.join(drive_path, filename)
            
            # Handle duplicate filenames
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(destination):
                new_filename = f"{base_name} ({counter}){ext}"
                destination = os.path.join(drive_path, new_filename)
                counter += 1
            
            shutil.copy2(file_path, destination)
            print(f"✅ Saved to Google Drive: {destination}")
            
            return destination
            
        except Exception as e:
            print(f"❌ Failed to save to Drive: {str(e)}")
            return None
    
    def list_drive_folders(self):
        """List available folders in Google Drive"""
        try:
            self.mount_drive()
            
            if not os.path.exists(self.base_path):
                return []
            
            folders = []
            for item in os.listdir(self.base_path):
                item_path = os.path.join(self.base_path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
            
            return sorted(folders)
            
        except Exception as e:
            print(f"❌ Failed to list folders: {str(e)}")
            return []

# ========== GUI INTERFACE ==========
class DailymotionDownloaderGUI:
    """GUI for Dailymotion Downloader"""
    
    def __init__(self):
        self.downloader = DailymotionDownloader()
        self.drive_manager = GoogleDriveManager()
        self.current_video_info = None
        self.download_progress = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # ========== URL INPUT SECTION ==========
        self.url_input = widgets.Textarea(
            value='',
            placeholder='Enter Dailymotion video URL\nExample: https://www.dailymotion.com/video/x8yzwz9',
            description='Video URL:',
            layout=widgets.Layout(width='90%', height='80px')
        )
        
        self.fetch_button = widgets.Button(
            description='🔍 Fetch Video Info',
            button_style='primary',
            layout=widgets.Layout(width='150px')
        )
        self.fetch_button.on_click(self.fetch_video_info)
        
        # ========== VIDEO INFO DISPLAY ==========
        self.video_title = widgets.HTML(value='<div style="color: #666">No video loaded</div>')
        self.video_thumbnail = widgets.Image(
            layout=widgets.Layout(width='320px', height='180px', border='1px solid #ddd')
        )
        self.video_details = widgets.HTML(value='')
        
        # ========== DOWNLOAD SETTINGS ==========
        self.quality_dropdown = widgets.Dropdown(
            options=['Loading...'],
            value=None,
            description='Quality:',
            disabled=True,
            layout=widgets.Layout(width='250px')
        )
        
        self.output_format = widgets.Dropdown(
            options=['mp4', 'mkv', 'webm'],
            value='mp4',
            description='Format:',
            layout=widgets.Layout(width='200px')
        )
        
        # ========== GOOGLE DRIVE SETTINGS ==========
        self.save_to_drive = widgets.Checkbox(
            value=True,
            description='Save to Google Drive',
            indent=False
        )
        
        self.drive_folder = widgets.Text(
            value='Dailymotion Downloads',
            placeholder='Folder name in Google Drive',
            description='Folder:',
            layout=widgets.Layout(width='300px')
        )
        
        self.browse_folders_button = widgets.Button(
            description='📁 Browse Folders',
            button_style='info',
            layout=widgets.Layout(width='150px')
        )
        self.browse_folders_button.on_click(self.browse_drive_folders)
        
        # ========== DOWNLOAD BUTTONS ==========
        self.download_button = widgets.Button(
            description='🎬 DOWNLOAD VIDEO',
            button_style='success',
            layout=widgets.Layout(width='200px', height='50px')
        )
        self.download_button.on_click(self.start_download)
        self.download_button.disabled = True
        
        self.cancel_button = widgets.Button(
            description='Cancel',
            button_style='danger',
            layout=widgets.Layout(width='100px', height='30px'),
            disabled=True
        )
        
        self.clear_button = widgets.Button(
            description='Clear',
            button_style='',
            layout=widgets.Layout(width='100px', height='30px')
        )
        self.clear_button.on_click(self.clear_all)
        
        # ========== PROGRESS DISPLAY ==========
        self.progress_bar = widgets.FloatProgress(
            value=0,
            min=0,
            max=100,
            description='Progress:',
            bar_style='info',
            layout=widgets.Layout(width='80%')
        )
        
        self.progress_label = widgets.Label(value='Ready')
        
        self.status_output = widgets.Output(
            layout=widgets.Layout(height='200px', overflow='auto', border='1px solid #ddd')
        )
        
        # ========== BUILD UI LAYOUT ==========
        self.ui = widgets.VBox([
            # Header
            widgets.HTML("<h1 style='color: #0D5BE3;'>🎬 Dailymotion Video Downloader</h1>"),
            widgets.HTML("<hr>"),
            
            # URL Section
            widgets.HTML("<h3>🔗 Enter Dailymotion URL</h3>"),
            self.url_input,
            self.fetch_button,
            widgets.HTML("<br>"),
            
            # Video Info Section
            widgets.HTML("<h3>📺 Video Information</h3>"),
            widgets.HBox([
                self.video_thumbnail,
                widgets.VBox([
                    self.video_title,
                    self.video_details
                ])
            ]),
            widgets.HTML("<br>"),
            
            # Download Settings
            widgets.HTML("<h3>⚙️ Download Settings</h3>"),
            widgets.HBox([
                self.quality_dropdown,
                self.output_format
            ]),
            widgets.HTML("<br>"),
            
            # Google Drive Settings
            widgets.HTML("<h3>📁 Google Drive Settings</h3>"),
            widgets.VBox([
                widgets.HBox([self.save_to_drive, self.drive_folder]),
                self.browse_folders_button
            ]),
            widgets.HTML("<br>"),
            
            # Action Buttons
            widgets.HBox([
                self.download_button,
                self.cancel_button,
                self.clear_button
            ]),
            widgets.HTML("<br>"),
            
            # Progress Section
            widgets.HTML("<h3>📊 Download Progress</h3>"),
            self.progress_label,
            self.progress_bar,
            widgets.HTML("<br>"),
            
            # Status Log
            widgets.HTML("<h3>📝 Activity Log</h3>"),
            self.status_output
        ])
    
    def display(self):
        """Display the GUI"""
        display(self.ui)
    
    def log(self, message, level="info"):
        """Add message to log - FIXED VERSION"""
        with self.status_output:
            colors = {
                "info": "black",
                "success": "green",
                "warning": "orange",
                "error": "red"
            }
            color = colors.get(level, "black")
            
            icons = {
                "info": "📝",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌"
            }
            icon = icons.get(level, "•")
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # FIX: Use HTML widget for colored output instead of print with unsafe_allow_html
            html_content = f'<span style="color:{color}">{timestamp} {icon} {message}</span>'
            display(HTML(html_content))
    
    def update_progress(self, value, message):
        """Update progress bar and label"""
        self.progress_bar.value = value
        self.progress_label.value = message
    
    def clear_all(self, b):
        """Clear all inputs and reset"""
        self.url_input.value = ''
        self.video_title.value = '<div style="color: #666">No video loaded</div>'
        self.video_thumbnail.value = b''
        self.video_details.value = ''
        self.quality_dropdown.options = ['Loading...']
        self.quality_dropdown.disabled = True
        self.download_button.disabled = True
        self.progress_bar.value = 0
        self.progress_label.value = 'Ready'
        
        with self.status_output:
            clear_output()
        
        self.log("🧹 Cleared all inputs", "info")
    
    def fetch_video_info(self, b):
        """Fetch video information from URL"""
        url = self.url_input.value.strip()
        
        if not url:
            self.log("❌ Please enter a Dailymotion URL", "error")
            return
        
        if 'dailymotion.com' not in url:
            self.log("⚠️ This doesn't look like a Dailymotion URL", "warning")
        
        self.log(f"🔍 Fetching video information...", "info")
        self.update_progress(10, "Fetching video info...")
        
        # Disable buttons during fetch
        self.fetch_button.disabled = True
        self.download_button.disabled = True
        
        try:
            # Extract video info
            video_info = self.downloader.extract_video_info(url)
            
            if not video_info:
                self.log("❌ Could not fetch video information", "error")
                self.fetch_button.disabled = False
                self.update_progress(0, "Failed to fetch video info")
                return
            
            self.current_video_info = video_info
            
            # Update UI with video info
            title = video_info.get('title', 'Unknown Title')
            self.video_title.value = f'<h3 style="margin: 0;">{title}</h3>'
            
            # Load thumbnail if available
            thumbnail_url = video_info.get('thumbnail')
            if thumbnail_url:
                try:
                    response = requests.get(thumbnail_url, timeout=10)
                    if response.status_code == 200:
                        self.video_thumbnail.value = response.content
                except:
                    pass
            
            # Show video details
            duration = video_info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            
            uploader = video_info.get('uploader', 'Unknown')
            views = video_info.get('view_count', 0)
            views_str = f"{views:,}" if views else "Unknown"
            
            details_html = f"""
            <div style="line-height: 1.6;">
                <strong>📊 Video Details:</strong><br>
                ⏱️ Duration: {duration_str}<br>
                👤 Uploader: {uploader}<br>
                👁️ Views: {views_str}<br>
                🆔 Video ID: {video_info.get('id', 'Unknown')}<br>
                📅 Upload Date: {video_info.get('upload_date', 'Unknown')}
            </div>
            """
            self.video_details.value = details_html
            
            # Get available qualities
            self.log("📡 Getting available video qualities...", "info")
            qualities = self.downloader.get_available_qualities(url)
            
            if qualities:
                quality_options = [q['display'] for q in qualities]
                self.quality_dropdown.options = quality_options
                self.quality_dropdown.value = quality_options[0]  # Highest quality
                self.quality_dropdown.disabled = False
                
                self.log(f"✅ Found {len(qualities)} quality options", "success")
                
                # Enable download button
                self.download_button.disabled = False
                
                self.update_progress(100, "Video info loaded successfully")
                self.log("✅ Video information loaded successfully", "success")
            else:
                self.log("⚠️ No quality options found, using default", "warning")
                self.quality_dropdown.options = ['Best available']
                self.quality_dropdown.value = 'Best available'
                self.quality_dropdown.disabled = False
                self.download_button.disabled = False
                
        except Exception as e:
            self.log(f"❌ Error fetching video info: {str(e)}", "error")
            self.update_progress(0, "Error fetching video info")
        
        finally:
            self.fetch_button.disabled = False
    
    def browse_drive_folders(self, b):
        """Browse existing Google Drive folders"""
        self.log("📁 Loading Google Drive folders...", "info")
        
        try:
            self.drive_manager.mount_drive()
            folders = self.drive_manager.list_drive_folders()
            
            if folders:
                # Create folder selection dialog
                folder_list = widgets.Select(
                    options=folders,
                    description='Folders:',
                    layout=widgets.Layout(width='300px', height='200px')
                )
                
                select_button = widgets.Button(
                    description='Use This Folder',
                    button_style='primary'
                )
                
                def select_folder(b):
                    selected = folder_list.value
                    if selected:
                        self.drive_folder.value = selected
                        self.log(f"✅ Selected folder: {selected}", "success")
                
                select_button.on_click(select_folder)
                
                dialog = widgets.VBox([
                    widgets.HTML("<h4>📁 Select Google Drive Folder</h4>"),
                    folder_list,
                    select_button
                ])
                
                display(dialog)
                self.log(f"Found {len(folders)} folders in Google Drive", "info")
            else:
                self.log("No folders found in Google Drive", "info")
                
        except Exception as e:
            self.log(f"❌ Error browsing folders: {str(e)}", "error")
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip('%')
            try:
                percent_float = float(percent)
                self.progress_bar.value = percent_float
                
                speed = d.get('_speed_str', '').strip()
                eta = d.get('_eta_str', '').strip()
                
                message = f"Downloading: {percent}%"
                if speed:
                    message += f" | Speed: {speed}"
                if eta:
                    message += f" | ETA: {eta}"
                
                self.progress_label.value = message
                
            except:
                pass
        
        elif d['status'] == 'finished':
            self.progress_bar.value = 100
            self.progress_label.value = "Processing file..."
    
    def start_download(self, b):
        """Start the download process"""
        if not self.current_video_info:
            self.log("❌ Please fetch video info first", "error")
            return
        
        # Disable buttons during download
        self.download_button.disabled = True
        self.fetch_button.disabled = True
        self.cancel_button.disabled = False
        
        # Start download in thread
        import threading
        thread = threading.Thread(target=self.download_video)
        thread.start()
    
    def download_video(self):
        """Download the video"""
        try:
            url = self.url_input.value.strip()
            quality_display = self.quality_dropdown.value
            
            # Extract quality from display string
            quality = 'best'
            if quality_display and quality_display != 'Best available':
                # Extract resolution from display (e.g., "1080p (1.23 GB)" -> "1080p")
                match = re.search(r'(\d+p)', quality_display)
                if match:
                    quality = match.group(1)
            
            self.log(f"🚀 Starting download...", "info")
            self.log(f"📥 Quality: {quality}", "info")
            self.log(f"🎬 Format: {self.output_format.value}", "info")
            
            # Create temporary directory
            temp_dir = '/content/dailymotion_downloads'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate filename
            title = self.current_video_info.get('title', 'video')
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            filename = f"{safe_title}.{self.output_format.value}"
            
            # Download video
            success, file_path, info = self.downloader.download_video(
                url=url,
                quality=quality,
                output_path=temp_dir,
                output_filename=filename,
                progress_callback=self.progress_hook
            )
            
            if success and file_path and os.path.exists(file_path):
                # Get file size
                file_size = os.path.getsize(file_path)
                size_str = self.downloader.format_size(file_size)
                
                self.log(f"✅ Download complete: {filename}", "success")
                self.log(f"📁 File size: {size_str}", "info")
                self.update_progress(100, f"Download complete! ({size_str})")
                
                # Save to Google Drive if enabled
                if self.save_to_drive.value:
                    self.log("💾 Saving to Google Drive...", "info")
                    drive_path = self.drive_manager.save_to_drive(
                        file_path, 
                        self.drive_folder.value
                    )
                    
                    if drive_path:
                        self.log(f"✅ Saved to Google Drive: {drive_path}", "success")
                        
                        # Offer to download from Drive
                        self.offer_drive_download(drive_path)
                    else:
                        self.log("❌ Failed to save to Google Drive", "error")
                        # Offer local download instead
                        self.offer_local_download(file_path)
                else:
                    # Offer local download
                    self.offer_local_download(file_path)
                
            else:
                self.log("❌ Download failed", "error")
                self.update_progress(0, "Download failed")
        
        except Exception as e:
            self.log(f"❌ Download error: {str(e)}", "error")
            self.update_progress(0, "Download failed")
        
        finally:
            # Re-enable buttons
            self.download_button.disabled = False
            self.fetch_button.disabled = False
            self.cancel_button.disabled = True
    
    def offer_local_download(self, file_path):
        """Offer to download file locally"""
        try:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                size_str = self.downloader.format_size(file_size)
                
                download_btn = widgets.Button(
                    description=f'⬇️ Download {filename} ({size_str})',
                    button_style='success',
                    layout=widgets.Layout(width='300px')
                )
                
                def download_file(b):
                    try:
                        files.download(file_path)
                        self.log("✅ Download started...", "success")
                    except Exception as e:
                        self.log(f"❌ Download error: {str(e)}", "error")
                
                download_btn.on_click(download_file)
                display(download_btn)
                
        except Exception as e:
            self.log(f"⚠️ Could not create download link: {str(e)}", "warning")
    
    def offer_drive_download(self, drive_path):
        """Show information about Drive-saved file"""
        try:
            filename = os.path.basename(drive_path)
            file_size = os.path.getsize(drive_path)
            size_str = self.downloader.format_size(file_size)
            
            info_html = f"""
            <div style="padding: 10px; background: #E8F5E9; border-radius: 5px; border: 1px solid #C8E6C9;">
                <strong>✅ Video saved to Google Drive:</strong><br>
                📁 Path: {drive_path}<br>
                📦 Size: {size_str}<br>
                💡 The file is now permanently stored in your Google Drive
            </div>
            """
            
            display(widgets.HTML(info_html))
            
            # Also offer local download
            self.offer_local_download(drive_path)
            
        except Exception as e:
            self.log(f"⚠️ Could not display Drive info: {str(e)}", "warning")

# ========== QUICK DOWNLOAD FUNCTION ==========
def quick_download(url, quality='best', save_to_drive=True, folder_name='Dailymotion Downloads'):
    """
    Quick function to download a Dailymotion video
    
    Args:
        url: Dailymotion video URL
        quality: Video quality ('best', 'worst', or specific like '720p')
        save_to_drive: Whether to save to Google Drive
        folder_name: Google Drive folder name
    
    Returns:
        Path to downloaded file
    """
    print(f"🎬 Quick download: {url}")
    
    downloader = DailymotionDownloader()
    drive_manager = GoogleDriveManager()
    
    # Get video info
    print("🔍 Fetching video information...")
    video_info = downloader.extract_video_info(url)
    
    if not video_info:
        print("❌ Could not fetch video information")
        return None
    
    print(f"📺 Title: {video_info.get('title')}")
    print(f"⏱️ Duration: {video_info.get('duration')} seconds")
    
    # Create temp directory
    temp_dir = '/content/quick_download'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Download video
    print(f"⬇️ Downloading video (quality: {quality})...")
    
    def simple_progress(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            print(f"Progress: {percent}", end='\r')
        elif d['status'] == 'finished':
            print("\n✅ Download complete!")
    
    success, file_path, info = downloader.download_video(
        url=url,
        quality=quality,
        output_path=temp_dir,
        progress_callback=simple_progress
    )
    
    if success and file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        size_str = downloader.format_size(file_size)
        print(f"📦 File size: {size_str}")
        
        # Save to Google Drive if requested
        if save_to_drive:
            print("💾 Saving to Google Drive...")
            drive_path = drive_manager.save_to_drive(file_path, folder_name)
            if drive_path:
                print(f"✅ Saved to Google Drive: {drive_path}")
                return drive_path
        
        return file_path
    else:
        print("❌ Download failed")
        return None

# ========== EXAMPLE URLS ==========
example_urls = """
Example Dailymotion URLs:
• https://www.dailymotion.com/video/x8yzwz9
• https://dailymotion.com/video/x8yzabc
• https://www.dailymotion.com/embed/video/x8yzwz9

Common Dailymotion URL patterns:
• https://www.dailymotion.com/video/{video_id}
• https://dailymotion.com/video/{video_id}
• https://www.dailymotion.com/embed/video/{video_id}
"""

# ========== MAIN EXECUTION ==========
def main():
    """Main function to run the downloader"""
    # Clear output
    clear_output()
    
    # Display banner
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║               🎬 DAILYMOTION VIDEO DOWNLOADER               ║
    ╠══════════════════════════════════════════════════════════════╣
    ║ Features:                                                   ║
    ║ • Download any Dailymotion video                           ║
    ║ • Multiple quality options (1080p, 720p, etc.)             ║
    ║ • Google Drive integration for permanent storage           ║
    ║ • Video preview with thumbnails                            ║
    ║ • Progress tracking                                        ║
    ║ • Safe filenames                                           ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    
    print(banner)
    print("\n" + "="*70)
    print("⚠️  LEGAL DISCLAIMER: Only download content you have rights to use")
    print("="*70 + "\n")
    
    # Display example URLs
    print(example_urls)
    print("-"*70)
    
    # Legal disclaimer
    disclaimer = widgets.HTML("""
    <div style="padding: 10px; background: #FFF3E0; border-left: 4px solid #FF9800; 
                border-radius: 5px; margin: 10px 0;">
    <strong>⚠️ LEGAL DISCLAIMER:</strong><br>
    This tool is for educational purposes only. Only download videos that you have 
    explicit permission to download or that are in the public domain. 
    Respect copyright laws and Dailymotion's Terms of Service.
    </div>
    """)
    display(disclaimer)
    
    # Display the GUI
    gui = DailymotionDownloaderGUI()
    gui.display()
    
    # Instructions
    instructions = widgets.Accordion(children=[
        widgets.VBox([
            widgets.HTML("<h4>📋 How to Use:</h4>"),
            widgets.HTML("""
            <ol>
            <li><strong>Find a video</strong> on dailymotion.com</li>
            <li><strong>Copy the URL</strong> from the address bar</li>
            <li><strong>Paste the URL</strong> in the box above</li>
            <li><strong>Click "Fetch Video Info"</strong> to load details</li>
            <li><strong>Choose quality</strong> from dropdown (highest is default)</li>
            <li><strong>Select format</strong> (MP4 recommended)</li>
            <li><strong>Choose Google Drive folder</strong> or use default</li>
            <li><strong>Click "DOWNLOAD VIDEO"</strong></li>
            <li><strong>Wait for completion</strong> and check Google Drive</li>
            </ol>
            """),
            widgets.HTML("<h4>💡 Tips:</h4>"),
            widgets.HTML("""
            <ul>
            <li>Use <strong>MP4 format</strong> for best compatibility</li>
            <li><strong>Google Drive</strong> saves files permanently</li>
            <li>Local downloads are <strong>temporary</strong> (Colab session only)</li>
            <li>Check video <strong>duration and size</strong> before downloading</li>
            <li>Some videos may have <strong>regional restrictions</strong></li>
            </ul>
            """),
        ])
    ])
    instructions.set_title(0, '📖 Instructions & Tips')
    display(instructions)
    
    # Quick function info
    print("\n" + "="*70)
    print("💡 Quick Command Usage:")
    print("quick_download('https://www.dailymotion.com/video/x8yzwz9', quality='720p')")
    print("="*70)
    
    return gui

# Run the application
if __name__ == "__main__":
    gui = main()
