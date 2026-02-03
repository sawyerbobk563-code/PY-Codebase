# tubi_downloader_colab_clean.ipynb
# Google Colab Notebook for Tubi Video Downloader with Clean Progress Bar

# @title =========================================
# @title 🎬 TUBI VIDEO DOWNLOADER - Clean Edition
# @title =========================================
# @markdown **For educational purposes only**

# @title =========================================
# @title 📦 INSTALLATION & SETUP
# @title =========================================

print("🚀 Setting up Tubi Downloader...")
print("⏳ This may take a few minutes...")

# Install required packages
!pip install -q yt-dlp
!apt-get update -qq && apt-get install -y -qq ffmpeg aria2 > /dev/null

print("✅ Installation complete!")

# @title =========================================
# @title 🔧 CONFIGURATION
# @title =========================================

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from google.colab import files, drive

# Setup paths
WORK_DIR = '/content/tubi_downloads'
Path(WORK_DIR).mkdir(exist_ok=True)
os.chdir(WORK_DIR)

print(f"📁 Working directory: {WORK_DIR}")

# Mount Google Drive (optional)
drive.mount('/content/drive', force_remount=True)
print("✅ Google Drive mounted at /content/drive")

# @title =========================================
# @title 📊 DOWNLOAD MANAGER WITH CLEAN PROGRESS
# @title =========================================

class DownloadManager:
    """Manages downloads with clean progress tracking"""
    
    def __init__(self):
        self.current_progress = 0
        self.last_update = 0
        self.start_time = None
        self.file_size = 0
        
    def progress_hook(self, d):
        """Clean progress hook - only updates at major milestones"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                percent = (downloaded / total) * 100
                
                # Only update at 5% intervals (or on start/finish)
                current_percent = int(percent)
                
                if current_percent != self.last_update:
                    # Update at 0%, 5%, 10%, ... 95%, 100%
                    if current_percent % 5 == 0 or current_percent == 100:
                        speed = d.get('speed', 0)
                        elapsed = time.time() - self.start_time if self.start_time else 0
                        
                        # Calculate ETA
                        if speed > 0 and percent < 100:
                            remaining_bytes = total - downloaded
                            eta_seconds = remaining_bytes / speed
                            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
                        else:
                            eta_str = "Calculating..."
                        
                        # Human readable sizes
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        speed_mb = speed / (1024 * 1024) if speed > 0 else 0
                        
                        # Create progress bar (25 chars)
                        bar_length = 25
                        filled = int(bar_length * percent / 100)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        
                        # Print progress (overwrites line)
                        sys.stdout.write(f'\r[{bar}] {percent:5.1f}% | '
                                       f'{downloaded_mb:6.1f}/{total_mb:6.1f} MB | '
                                       f'{speed_mb:5.1f} MB/s | ETA: {eta_str}')
                        sys.stdout.flush()
                        
                        self.last_update = current_percent
                        
        elif d['status'] == 'finished':
            elapsed = time.time() - self.start_time
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
            sys.stdout.write(f'\r{" " * 100}\r')  # Clear line
            print(f"✅ Download completed in {elapsed_str}")
            self.last_update = 100

# @title =========================================
# @title 🚀 CLEAN DOWNLOAD FUNCTION
# @title =========================================

def download_tubi_clean(url, quality='best', output_dir='downloads', 
                        download_manager=None, video_number=None, total_videos=None):
    """
    Clean download function with minimal printing
    """
    import yt_dlp
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Initialize download manager if not provided
    if download_manager is None:
        download_manager = DownloadManager()
    
    # Setup download manager
    download_manager.start_time = time.time()
    download_manager.last_update = -1
    
    # Show download start info
    prefix = ""
    if video_number is not None and total_videos is not None:
        prefix = f"[{video_number}/{total_videos}] "
    
    print(f"\n{prefix}📥 Starting download: {url}")
    print(f"{prefix}🎯 Quality: {quality}")
    print(f"{prefix}📂 Output: {output_dir}")
    print("-" * 70)
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'best' if quality == 'best' else f'best[height<={quality.replace("p", "")}]',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'quiet': True,  # Supress yt-dlp output
        'no_warnings': True,
        'progress_hooks': [download_manager.progress_hook],
        'merge_output_format': 'mp4',
        'retries': 10,
        'fragment_retries': 10,
        'external_downloader': 'aria2c',
        'external_downloader_args': [
            '--split=16',
            '--max-connection-per-server=16',
            '--min-split-size=1M',
            '--file-allocation=none'
        ],
        'concurrent_fragment_downloads': 16,
        'noprogress': True,  # Don't show yt-dlp's progress
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get output filename
            output_file = ydl.prepare_filename(info)
            
            # Clean up filename
            if output_file.endswith('.webm.part'):
                output_file = output_file.replace('.webm.part', '.mp4')
            elif output_file.endswith('.webm'):
                output_file = output_file.replace('.webm', '.mp4')
            elif output_file.endswith('.part'):
                output_file = output_file.replace('.part', '')
            
            # Get file size
            if os.path.exists(output_file):
                size_mb = os.path.getsize(output_file) / (1024 * 1024)
                title = info.get('title', 'Unknown')[:50]
                print(f"\n{prefix}✅ Download complete: {title}")
                print(f"{prefix}📄 File: {output_file}")
                print(f"{prefix}💾 Size: {size_mb:.1f} MB")
            else:
                print(f"\n{prefix}⚠️  File not found after download")
            
            return output_file
            
    except Exception as e:
        print(f"\n{prefix}❌ Download failed: {str(e)[:100]}")
        return None

# @title =========================================
# @title 🎮 INTERACTIVE DOWNLOADER (CLEAN)
# @title =========================================

from IPython.display import display, HTML, clear_output
import ipywidgets as widgets

def create_clean_downloader():
    """Create clean interactive downloader"""
    
    # URL input
    url_text = widgets.Text(
        value='',
        placeholder='Enter Tubi URL (e.g., https://tubitv.com/movies/12345)',
        description='URL:',
        layout=widgets.Layout(width='80%')
    )
    
    # Quality selector
    quality_dropdown = widgets.Dropdown(
        options=['best', '1080p', '720p', '480p', '360p'],
        value='best',
        description='Quality:',
        disabled=False,
    )
    
    # Output folder
    output_text = widgets.Text(
        value='downloads',
        placeholder='Output folder',
        description='Folder:',
        layout=widgets.Layout(width='50%')
    )
    
    # Save to Drive checkbox
    drive_checkbox = widgets.Checkbox(
        value=False,
        description='Save to Google Drive',
        disabled=False,
        indent=False
    )
    
    # Drive path
    drive_text = widgets.Text(
        value='/content/drive/MyDrive/tubi_downloads',
        placeholder='Drive path',
        description='Drive:',
        layout=widgets.Layout(width='60%'),
        disabled=True
    )
    
    def on_drive_change(change):
        drive_text.disabled = not change['new']
    
    drive_checkbox.observe(on_drive_change, names='value')
    
    # Download button
    download_button = widgets.Button(
        description='📥 Download Video',
        button_style='success',
        layout=widgets.Layout(width='200px'),
        icon='download'
    )
    
    # Progress bar
    progress_bar = widgets.FloatProgress(
        value=0,
        min=0,
        max=100,
        description='Progress:',
        bar_style='info',
        style={'bar_color': '#4CAF50'},
        layout=widgets.Layout(width='80%', visibility='hidden')
    )
    
    # Status output
    status_output = widgets.Output()
    
    # Info button
    info_button = widgets.Button(
        description='ℹ️ Get Info',
        button_style='info',
        layout=widgets.Layout(width='150px'),
        icon='info'
    )
    
    # Batch section
    batch_upload = widgets.FileUpload(
        accept='.txt',
        multiple=False,
        description='Upload URLs',
        layout=widgets.Layout(width='250px')
    )
    
    batch_button = widgets.Button(
        description='📚 Batch Download',
        button_style='warning',
        layout=widgets.Layout(width='200px'),
        icon='copy'
    )
    
    # Speed selector
    speed_dropdown = widgets.Dropdown(
        options=['Normal', 'Fast', 'Slow'],
        value='Normal',
        description='Speed:',
        layout=widgets.Layout(width='150px')
    )
    
    def on_download_click(b):
        with status_output:
            clear_output(wait=True)
            
            url = url_text.value.strip()
            if not url:
                print("❌ Please enter a URL")
                return
            
            # Determine output directory
            if drive_checkbox.value and drive_text.value.strip():
                output_dir = drive_text.value.strip()
            else:
                output_dir = output_text.value
            
            print("🚀 Initializing download...")
            
            # Show progress bar
            progress_bar.layout.visibility = 'visible'
            progress_bar.value = 0
            
            # Create a custom progress hook for widget
            def widget_progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    
                    if total > 0:
                        percent = (downloaded / total) * 100
                        progress_bar.value = percent
            
            # Custom download with widget progress
            result = download_tubi_with_widget(url, quality_dropdown.value, output_dir, 
                                             widget_progress_hook, speed_dropdown.value)
            
            # Hide progress bar
            progress_bar.layout.visibility = 'hidden'
            
            if result:
                print(f"\n✅ Download successful!")
                print(f"📁 Saved to: {result}")
                
                # Offer download if not on Drive
                if not drive_checkbox.value:
                    try:
                        files.download(result)
                        print("⬇️ File download started")
                    except:
                        print("💡 File saved locally")
            else:
                print("❌ Download failed")
    
    def on_info_click(b):
        with status_output:
            clear_output(wait=True)
            
            url = url_text.value.strip()
            if not url:
                print("❌ Please enter a URL")
                return
            
            print("🔍 Fetching video information...")
            
            try:
                import yt_dlp
                ydl_opts = {'quiet': True}
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Display info in a clean format
                    display(HTML(f"""
                    <div style="background:#f5f5f5;padding:15px;border-radius:5px;margin:10px 0;">
                    <h3 style="margin-top:0;">📊 Video Information</h3>
                    <table style="width:100%;">
                    <tr><td><strong>🎬 Title:</strong></td><td>{info.get('title', 'N/A')}</td></tr>
                    <tr><td><strong>⏱️ Duration:</strong></td><td>{info.get('duration', 0)} seconds</td></tr>
                    <tr><td><strong>📺 Channel:</strong></td><td>{info.get('channel', 'N/A')}</td></tr>
                    <tr><td><strong>📅 Upload Date:</strong></td><td>{info.get('upload_date', 'N/A')}</td></tr>
                    </table>
                    </div>
                    """))
                    
                    # Available qualities
                    formats = info.get('formats', [])
                    if formats:
                        qualities = sorted(set(
                            f"{f.get('height', 0)}p" 
                            for f in formats 
                            if f.get('height')
                        ), reverse=True)
                        
                        if qualities:
                            print(f"📈 Available Qualities: {', '.join(qualities)}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def on_batch_click(b):
        with status_output:
            clear_output(wait=True)
            
            if not batch_upload.value:
                print("❌ Please upload a URLs file first")
                return
            
            # Get uploaded file
            uploaded = list(batch_upload.value.values())[0]
            content = uploaded['content'].decode('utf-8')
            urls = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not urls:
                print("❌ No URLs found in file")
                return
            
            # Limit to reasonable number
            max_urls = 5
            if len(urls) > max_urls:
                print(f"⚠️  Limiting to first {max_urls} URLs (out of {len(urls)})")
                urls = urls[:max_urls]
            
            print(f"📚 Processing {len(urls)} URLs")
            print("=" * 50)
            
            # Determine output directory
            if drive_checkbox.value and drive_text.value.strip():
                output_dir = drive_text.value.strip()
            else:
                output_dir = output_text.value
            
            # Create download manager
            dm = DownloadManager()
            
            # Download each URL
            success_count = 0
            for i, url in enumerate(urls, 1):
                print(f"\n📥 Download {i}/{len(urls)}")
                result = download_tubi_clean(url, quality_dropdown.value, 
                                           output_dir, dm, i, len(urls))
                if result:
                    success_count += 1
                
                # Small delay between downloads
                if i < len(urls):
                    time.sleep(1)
            
            # Summary
            print("\n" + "=" * 50)
            print(f"📊 Batch Complete: {success_count}/{len(urls)} successful")
            
            # Create zip if any succeeded
            if success_count > 0 and not drive_checkbox.value:
                print("\n📦 Creating zip archive...")
                !zip -q -r batch_downloads.zip {output_dir}/*
                print("✅ Zip created: batch_downloads.zip")
                
                try:
                    files.download('batch_downloads.zip')
                except:
                    pass
    
    def download_tubi_with_widget(url, quality, output_dir, progress_hook, speed='Normal'):
        """Download with widget progress tracking"""
        import yt_dlp
        
        # Speed settings
        speed_settings = {
            'Slow': {'concurrent_fragment_downloads': 4, 'retries': 5},
            'Normal': {'concurrent_fragment_downloads': 8, 'retries': 10},
            'Fast': {'concurrent_fragment_downloads': 16, 'retries': 15}
        }
        
        settings = speed_settings.get(speed, speed_settings['Normal'])
        
        ydl_opts = {
            'format': 'best' if quality == 'best' else f'best[height<={quality.replace("p", "")}]',
            'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'retries': settings['retries'],
            'fragment_retries': settings['retries'],
            'external_downloader': 'aria2c',
            'external_downloader_args': [
                '--split=16',
                f'--max-connection-per-server={settings["concurrent_fragment_downloads"]}',
                '--min-split-size=1M'
            ],
            'concurrent_fragment_downloads': settings['concurrent_fragment_downloads'],
            'noprogress': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                output_file = ydl.prepare_filename(info)
                
                # Clean filename
                if output_file.endswith('.webm.part'):
                    output_file = output_file.replace('.webm.part', '.mp4')
                elif output_file.endswith('.part'):
                    output_file = output_file.replace('.part', '')
                
                return output_file
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    # Connect buttons
    download_button.on_click(on_download_click)
    info_button.on_click(on_info_click)
    batch_button.on_click(on_batch_click)
    
    # Display interface
    display(HTML("<h2>🎬 Tubi Video Downloader</h2>"))
    display(HTML("<p>Clean interface with minimal output</p>"))
    
    # Create form
    form = widgets.VBox([
        widgets.HBox([widgets.Label("Enter Tubi URL:")]),
        widgets.HBox([url_text]),
        widgets.HBox([quality_dropdown, speed_dropdown]),
        widgets.HBox([widgets.Label("Output:"), output_text]),
        widgets.HBox([drive_checkbox, drive_text]),
        widgets.HBox([download_button, info_button, batch_button]),
        widgets.HBox([batch_upload]),
        progress_bar,
        status_output
    ])
    
    display(form)

# @title =========================================
# @title 📁 FILE MANAGER (CLEAN)
# @title =========================================

def clean_file_manager():
    """Clean file manager with download options"""
    
    print("📁 File Manager")
    print("=" * 50)
    
    # List files
    files_list = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(('.mp4', '.mkv', '.webm', '.avi')):
                files_list.append(os.path.join(root, file))
    
    if not files_list:
        print("No video files found")
        return
    
    # Display files
    print(f"Found {len(files_list)} video files:")
    print("-" * 40)
    
    for i, file_path in enumerate(files_list[:10], 1):
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        file_name = os.path.basename(file_path)[:40]
        print(f"{i:2d}. {file_name:40} {size_mb:6.1f} MB")
    
    # Download options
    print("\n" + "=" * 50)
    print("Download Options:")
    
    # Create download buttons
    button_box = widgets.VBox()
    buttons = []
    
    for i, file_path in enumerate(files_list[:5], 1):
        btn = widgets.Button(
            description=f"⬇️ Download {os.path.basename(file_path)[:20]}...",
            layout=widgets.Layout(width='300px')
        )
        
        def create_handler(path):
            def handler(b):
                try:
                    files.download(path)
                    print(f"✅ Download started: {os.path.basename(path)}")
                except Exception as e:
                    print(f"❌ Error: {e}")
            return handler
        
        btn.on_click(create_handler(file_path))
        buttons.append(btn)
    
    button_box.children = buttons
    display(button_box)
    
    # Zip all button
    if len(files_list) > 1:
        zip_btn = widgets.Button(
            description='📦 Zip All Videos',
            button_style='success',
            layout=widgets.Layout(width='200px')
        )
        
        def zip_all(b):
            print("Creating zip archive...")
            !zip -q -r all_videos.zip *.mp4 *.mkv *.webm *.avi 2>/dev/null || true
            try:
                files.download('all_videos.zip')
                print("✅ Zip download started")
            except:
                print("❌ Could not create zip")
        
        zip_btn.on_click(zip_all)
        display(zip_btn)

# @title =========================================
# @title 🚀 QUICK COMMANDS
# @title =========================================

# @markdown ### **Quick Download (One Line)**
def quick_download(url, quality='720p'):
    """
    Quick one-line download
    Example: quick_download('https://tubitv.com/movies/12345')
    """
    print(f"🚀 Quick download: {url}")
    print(f"🎯 Quality: {quality}")
    print("-" * 40)
    
    dm = DownloadManager()
    result = download_tubi_clean(url, quality, 'quick_downloads', dm)
    
    if result:
        print(f"\n✅ Quick download complete!")
        try:
            files.download(result)
        except:
            print(f"💾 Saved to: {result}")
    else:
        print("❌ Quick download failed")
    
    return result

# @markdown ### **Batch Download from List**
def batch_download_urls(urls, quality='720p'):
    """
    Download multiple URLs
    Example: batch_download_urls(['url1', 'url2'], '720p')
    """
    print(f"📚 Batch download of {len(urls)} URLs")
    print("=" * 50)
    
    dm = DownloadManager()
    success_count = 0
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Downloading...")
        result = download_tubi_clean(url, quality, 'batch_downloads', dm, i, len(urls))
        if result:
            success_count += 1
    
    print(f"\n📊 Completed: {success_count}/{len(urls)} successful")
    return success_count

# @title =========================================
# @title 📋 USAGE EXAMPLES
# @title =========================================

# @markdown ### **Example 1: Interactive Downloader**
print("Run this to open the interactive downloader:")
print("create_clean_downloader()")

# @markdown ### **Example 2: Quick Download**
example_code = """
# Single video download
quick_download('https://tubitv.com/movies/12345', '720p')

# Or use the clean function directly
download_tubi_clean('https://tubitv.com/movies/12345', '1080p', 'my_downloads')
"""

print(example_code)

# @markdown ### **Example 3: Batch from File**
batch_example = """
# Create a file with URLs
urls = [
    'https://tubitv.com/movies/12345',
    'https://tubitv.com/movies/67890',
]

with open('urls.txt', 'w') as f:
    f.write('\\n'.join(urls))

# Then use the interactive batch downloader
# or call batch_download_urls(urls)
"""

print(batch_example)

# @markdown ### **Example 4: Save to Google Drive**
drive_example = """
# Download directly to Google Drive
download_tubi_clean(
    'https://tubitv.com/movies/12345',
    '720p',
    '/content/drive/MyDrive/tubi_downloads'
)
"""

print(drive_example)

# @title =========================================
# @title 🎯 MAIN INTERFACE
# @title =========================================

print("🎬 TUBI DOWNLOADER READY!")
print("=" * 50)
print("\nChoose an option:")
print("1. create_clean_downloader() - Interactive interface")
print("2. quick_download(url) - Fast single download")
print("3. clean_file_manager() - Manage downloaded files")
print("4. batch_download_urls(urls) - Batch download")
print("\nExample: quick_download('https://tubitv.com/movies/12345', '720p')")

# @title =========================================
# @title ⚠️  DISCLAIMER
# @title =========================================

disclaimer_html = """
<div style="background:#fff3cd;border:1px solid #ffeaa7;border-radius:5px;padding:15px;margin:20px 0;">
<h3 style="color:#856404;margin-top:0;">⚠️ LEGAL DISCLAIMER</h3>
<p style="color:#856404;margin-bottom:0;">
This tool is for <strong>EDUCATIONAL PURPOSES ONLY</strong>.<br>
• Only download content you have rights to access<br>
• Respect copyright laws and terms of service<br>
• The developers are not responsible for misuse<br>
• By using this tool, you agree to use it responsibly and legally
</p>
</div>
"""

display(HTML(disclaimer_html))

# @title =========================================
# @title 🚀 READY TO START
# @title =========================================

print("\n" + "=" * 50)
print("✅ Setup complete! Choose your download method above.")
print("=" * 50)

# Launch the interactive downloader by default
print("\n📱 Launching interactive downloader...")
create_clean_downloader()
