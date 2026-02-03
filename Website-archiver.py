# web_archiver_colab_drive.ipynb
# Complete Webpage Archiver with Google Drive Integration

# @title =========================================
# @title 🌐 WEBPAGE ARCHIVER PRO - Google Drive Edition
# @title =========================================
# @markdown **For educational purposes only**

# @title =========================================
# @title 📦 INSTALL & SETUP
# @title =========================================

print("🚀 Setting up Web Archiver Pro...")
print("⏳ Installing dependencies...")

!pip install -q requests beautifulsoup4 tqdm
!apt-get update -qq && apt-get install -y -qq tree > /dev/null

print("✅ Dependencies installed!")

# @title =========================================
# @title 🔧 IMPORT LIBRARIES
# @title =========================================

import os
import sys
import re
import json
import time
import shutil
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag
from tqdm.notebook import tqdm
from google.colab import files, drive, output

print("📚 Importing libraries...")

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

print("✅ Libraries imported!")

# @title =========================================
# @title 🗂️ GOOGLE DRIVE SETUP
# @title =========================================

class GoogleDriveManager:
    """Manage Google Drive operations"""
    
    def __init__(self):
        self.drive_mounted = False
        self.base_drive_path = None
        
    def mount_drive(self, mount_point='/content/drive'):
        """Mount Google Drive"""
        try:
            print("📁 Mounting Google Drive...")
            drive.mount(mount_point)
            self.drive_mounted = True
            self.base_drive_path = Path(mount_point) / 'MyDrive'
            print(f"✅ Google Drive mounted at: {self.base_drive_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to mount Google Drive: {e}")
            return False
    
    def create_drive_folder(self, folder_name="web_archives", subfolder=None):
        """Create folder in Google Drive"""
        if not self.drive_mounted:
            if not self.mount_drive():
                return None
        
        try:
            # Create main archive folder
            archive_path = self.base_drive_path / folder_name
            archive_path.mkdir(exist_ok=True)
            
            # Create subfolder if specified
            if subfolder:
                subfolder_path = archive_path / subfolder
                subfolder_path.mkdir(exist_ok=True)
                return subfolder_path
            else:
                return archive_path
                
        except Exception as e:
            print(f"❌ Failed to create Drive folder: {e}")
            return None
    
    def copy_to_drive(self, source_path, drive_path):
        """Copy files/folders to Google Drive"""
        if not self.drive_mounted:
            if not self.mount_drive():
                return False
        
        try:
            source = Path(source_path)
            destination = Path(drive_path)
            
            print(f"📤 Copying to Google Drive: {drive_path}")
            
            if source.is_file():
                # Copy single file
                shutil.copy2(source, destination)
                print(f"✅ Copied file: {source.name}")
            else:
                # Copy entire directory
                if destination.exists():
                    # Copy contents
                    for item in source.rglob('*'):
                        if item.is_file():
                            rel_path = item.relative_to(source)
                            dest_item = destination / rel_path
                            dest_item.parent.mkdir(exist_ok=True, parents=True)
                            shutil.copy2(item, dest_item)
                else:
                    # Copy entire directory
                    shutil.copytree(source, destination, dirs_exist_ok=True)
                
                print(f"✅ Copied directory: {source.name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to copy to Drive: {e}")
            return False
    
    def sync_to_drive(self, local_path, drive_path, delete_original=False):
        """Sync files to Drive and optionally delete original"""
        if self.copy_to_drive(local_path, drive_path):
            if delete_original:
                try:
                    shutil.rmtree(local_path)
                    print(f"🗑️  Deleted local copy: {local_path}")
                except:
                    print(f"⚠️  Could not delete local copy")
            return True
        return False

# Initialize Drive Manager
drive_manager = GoogleDriveManager()

# @title =========================================
# @title ⚙️ CONFIGURATION
# @title =========================================

class Config:
    """Configuration settings"""
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    
    TIMEOUT = 30
    MAX_RETRIES = 3
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2GB for Colab
    MAX_PAGES = 100
    MAX_WORKERS = 8
    
    # File types to download
    RESOURCE_EXTENSIONS = {
        '.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', 
        '.ico', '.ttf', '.otf', '.woff', '.woff2', '.eot',
        '.pdf', '.zip', '.mp4', '.mp3', '.wav', '.avi', '.mov',
        '.xml', '.json', '.txt', '.csv'
    }
    
    RESPECT_ROBOTS = True
    CREATE_LOCAL_SERVER = True
    MODIFY_HTML_FOR_LOCAL = True
    SAVE_TO_DRIVE = True  # Auto-save to Google Drive
    COMPRESS_ARCHIVE = True  # Create ZIP file

# @title =========================================
# @title 🚀 ADVANCED WEB ARCHIVER
# @title =========================================

class AdvancedWebArchiver:
    """Advanced webpage archiver with Drive integration"""
    
    def __init__(self, base_url, output_dir=None, config=None, auto_mount_drive=True):
        """Initialize archiver with Drive support"""
        
        # Validate and parse URL
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = 'https://' + base_url
            parsed = urlparse(base_url)
        
        self.base_url = base_url
        self.base_domain = parsed.netloc
        self.scheme = parsed.scheme
        self.original_url = base_url
        
        # Setup configuration
        self.config = config or Config()
        
        # Setup Drive
        self.drive_manager = GoogleDriveManager()
        self.drive_path = None
        
        if auto_mount_drive and self.config.SAVE_TO_DRIVE:
            self.drive_manager.mount_drive()
        
        # Setup output directories
        self.setup_directories(output_dir)
        
        # Setup session
        self.session = self._create_session()
        
        # Tracking
        self.visited_urls = set()
        self.urls_to_visit = {self.base_url}
        self.url_to_local = {}
        self.resource_queue = []
        
        # Statistics
        self.stats = {
            'total_pages': 0,
            'total_files': 0,
            'total_size': 0,
            'start_time': time.time(),
            'html_files': 0,
            'css_files': 0,
            'js_files': 0,
            'images': 0,
            'fonts': 0,
            'other_files': 0,
            'failed_downloads': 0,
        }
        
        # Progress tracking
        self.progress = {
            'current': 0,
            'total': 0,
            'current_file': '',
            'speed': 0,
            'eta': 0
        }
        
        # Robots.txt
        self.robots_rules = {}
        if self.config.RESPECT_ROBOTS:
            self.load_robots_txt()
        
        print(f"✅ Archiver initialized for: {self.base_url}")
        print(f"📁 Local: {self.output_dir}")
        if self.drive_path:
            print(f"📁 Drive: {self.drive_path}")
    
    def setup_directories(self, output_dir=None):
        """Setup local and Drive directories"""
        
        # Generate folder name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_domain = re.sub(r'[^\w\-\.]', '_', self.base_domain)
        folder_name = f'{safe_domain}_{timestamp}'
        
        # Local directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(f'/content/web_archives/{folder_name}')
        
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Subdirectories
        self.assets_dir = self.output_dir / 'assets'
        self.assets_dir.mkdir(exist_ok=True)
        
        self.css_dir = self.assets_dir / 'css'
        self.js_dir = self.assets_dir / 'js'
        self.images_dir = self.assets_dir / 'images'
        self.fonts_dir = self.assets_dir / 'fonts'
        self.media_dir = self.assets_dir / 'media'
        
        for dir in [self.css_dir, self.js_dir, self.images_dir, self.fonts_dir, self.media_dir]:
            dir.mkdir(exist_ok=True)
        
        # Google Drive directory
        if self.config.SAVE_TO_DRIVE:
            self.drive_path = self.drive_manager.create_drive_folder(
                folder_name="web_archives",
                subfolder=folder_name
            )
    
    def _create_session(self):
        """Create HTTP session with retry logic"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100
        )
        
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(self.config.HEADERS)
        
        return session
    
    def load_robots_txt(self):
        """Load and parse robots.txt"""
        robots_url = f"{self.scheme}://{self.base_domain}/robots.txt"
        
        try:
            response = self.session.get(robots_url, timeout=self.config.TIMEOUT)
            if response.status_code == 200:
                self.parse_robots_txt(response.text)
                print(f"✅ Loaded robots.txt")
            else:
                print(f"ℹ️  No robots.txt found (Status: {response.status_code})")
        except Exception as e:
            print(f"⚠️  Could not load robots.txt: {e}")
    
    def parse_robots_txt(self, content):
        """Parse robots.txt content"""
        current_agent = None
        
        for line in content.split('\n'):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if line.lower().startswith('user-agent:'):
                current_agent = line.split(':', 1)[1].strip()
                if current_agent not in self.robots_rules:
                    self.robots_rules[current_agent] = {'allow': [], 'disallow': []}
            
            elif line.lower().startswith('disallow:') and current_agent:
                path = line.split(':', 1)[1].strip()
                self.robots_rules[current_agent]['disallow'].append(path)
            
            elif line.lower().startswith('allow:') and current_agent:
                path = line.split(':', 1)[1].strip()
                self.robots_rules[current_agent]['allow'].append(path)
    
    def is_allowed_by_robots(self, url):
        """Check if URL is allowed by robots.txt"""
        if not self.config.RESPECT_ROBOTS:
            return True
        
        parsed = urlparse(url)
        path = parsed.path
        
        # Check all agents (including wildcard *)
        for agent, rules in self.robots_rules.items():
            # Skip if not applicable (unless wildcard or our user agent)
            if agent not in ['*', self.config.USER_AGENT] and agent != self.config.USER_AGENT:
                continue
            
            # Check disallow rules
            for disallow in rules['disallow']:
                if disallow and path.startswith(disallow):
                    # Check for more specific allow rule
                    allowed = False
                    for allow in rules['allow']:
                        if path.startswith(allow) and len(allow) > len(disallow):
                            allowed = True
                            break
                    
                    if not allowed:
                        return False
        
        return True
    
    # ============================================================================
    # URL PROCESSING
    # ============================================================================
    
    def normalize_url(self, url, base_url=None):
        """Normalize URL to absolute form"""
        if not url or url.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'sms:')):
            return None
        
        # Remove fragment
        url, _ = urldefrag(url)
        
        # Handle data URLs
        if url.startswith('data:'):
            return url
        
        if base_url is None:
            base_url = self.base_url
        
        # Make relative URLs absolute
        if not urlparse(url).scheme:
            url = urljoin(base_url, url)
        
        return url
    
    def is_resource_url(self, url):
        """Check if URL is a downloadable resource"""
        if not url:
            return False
        
        if url.startswith('data:'):
            return True
        
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check extensions
        for ext in self.config.RESOURCE_EXTENSIONS:
            if path.endswith(ext):
                return True
        
        # Check by content-type patterns
        resource_patterns = [
            r'\.(css|js|jpg|jpeg|png|gif|webp|svg|ico|ttf|otf|woff|woff2|eot|pdf|mp4|mp3|wav|avi|mov)$',
            r'/static/',
            r'/assets/',
            r'/images/',
            r'/css/',
            r'/js/',
            r'/fonts/',
            r'/media/',
        ]
        
        for pattern in resource_patterns:
            if re.search(pattern, path):
                return True
        
        return False
    
    def get_file_category(self, url, content_type=None):
        """Determine file category for organization"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check by extension first
        if path.endswith('.css') or (content_type and 'css' in content_type.lower()):
            return 'css'
        elif path.endswith('.js') or (content_type and 'javascript' in content_type.lower()):
            return 'js'
        elif any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico']):
            return 'image'
        elif any(path.endswith(ext) for ext in ['.ttf', '.otf', '.woff', '.woff2', '.eot']):
            return 'font'
        elif any(path.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.wav', '.mp3']):
            return 'media'
        elif path.endswith('.pdf') or (content_type and 'pdf' in content_type.lower()):
            return 'pdf'
        else:
            return 'other'
    
    def generate_local_path(self, url, category=None, content_type=None):
        """Generate local file path with organization"""
        
        if category is None:
            category = self.get_file_category(url, content_type)
        
        parsed = urlparse(url)
        path = parsed.path
        
        if not path or path == '/':
            filename = 'index.html'
        else:
            # Extract filename
            filename = os.path.basename(path)
            if not filename:
                filename = 'index.html'
        
        # Clean filename
        def clean_filename(name):
            name, ext = os.path.splitext(name)
            # Remove query string if present
            name = name.split('?')[0]
            # Replace invalid characters
            name = re.sub(r'[^\w\-\.]', '_', name)
            # Limit length
            if len(name) > 100:
                hash_part = hashlib.md5(name.encode()).hexdigest()[:8]
                name = name[:80] + '_' + hash_part
            return name + ext
        
        filename = clean_filename(filename)
        
        # Organize by category
        if category == 'css':
            return self.css_dir / filename
        elif category == 'js':
            return self.js_dir / filename
        elif category == 'image':
            return self.images_dir / filename
        elif category == 'font':
            return self.fonts_dir / filename
        elif category == 'media':
            return self.media_dir / filename
        elif category == 'pdf':
            return self.output_dir / 'documents' / filename
        else:
            # For HTML and unknown files, preserve original path structure
            if not path or path == '/':
                return self.output_dir / 'index.html'
            else:
                # Clean path components
                parts = path.split('/')
                clean_parts = []
                for part in parts:
                    if part:
                        clean_parts.append(clean_filename(part))
                
                # Ensure .html extension for pages
                if clean_parts and not os.path.splitext(clean_parts[-1])[1]:
                    clean_parts[-1] += '.html'
                
                return self.output_dir / '/'.join(clean_parts)
    
    # ============================================================================
    # DOWNLOAD ENGINE
    # ============================================================================
    
    def download_with_progress(self, url, local_path=None):
        """Download file with progress tracking"""
        try:
            # Check cache
            if url in self.url_to_local:
                cached_path = self.url_to_local[url]
                if cached_path.exists():
                    size = cached_path.stat().st_size
                    self.stats['total_size'] += size
                    return True, cached_path, 'cached', size
            
            # Prepare request
            headers = self.config.HEADERS.copy()
            
            # Make request
            start_time = time.time()
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.config.TIMEOUT,
                stream=True
            )
            
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('Content-Length')
            if content_length:
                file_size = int(content_length)
                if file_size > self.config.MAX_FILE_SIZE:
                    print(f"⚠️  File too large ({file_size} bytes): {url}")
                    return False, None, None, 0
            
            # Determine local path
            content_type = response.headers.get('Content-Type', '')
            category = self.get_file_category(url, content_type)
            
            if local_path is None:
                local_path = self.generate_local_path(url, category, content_type)
            
            # Create directory
            local_path.parent.mkdir(exist_ok=True, parents=True)
            
            # Download with progress
            file_size = 0
            chunk_size = 8192
            
            with open(local_path, 'wb') as f, tqdm(
                desc=os.path.basename(str(local_path))[:30],
                total=int(content_length) if content_length else None,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as pbar:
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        chunk_len = len(chunk)
                        file_size += chunk_len
                        pbar.update(chunk_len)
                        
                        # Check size during download
                        if file_size > self.config.MAX_FILE_SIZE:
                            print(f"⚠️  File exceeded size limit: {url}")
                            local_path.unlink(missing_ok=True)
                            return False, None, None, 0
            
            # Update statistics
            download_time = time.time() - start_time
            speed = file_size / download_time if download_time > 0 else 0
            
            self.stats['total_size'] += file_size
            self.stats['total_files'] += 1
            
            # Update category stats
            if category == 'css':
                self.stats['css_files'] += 1
            elif category == 'js':
                self.stats['js_files'] += 1
            elif category == 'image':
                self.stats['images'] += 1
            elif category == 'font':
                self.stats['fonts'] += 1
            else:
                self.stats['other_files'] += 1
            
            # Cache the URL
            self.url_to_local[url] = local_path
            
            print(f"✅ Downloaded: {os.path.basename(str(local_path))} ({file_size/1024:.1f} KB)")
            
            return True, local_path, content_type, file_size
            
        except Exception as e:
            self.stats['failed_downloads'] += 1
            print(f"❌ Failed: {url} - {str(e)[:100]}")
            return False, None, None, 0
    
    # ============================================================================
    # HTML PROCESSING
    # ============================================================================
    
    def process_html_file(self, url, local_path):
        """Process HTML file for local viewing"""
        try:
            with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            base_dir = local_path.parent
            
            # Update all links
            self.update_html_links(soup, url, base_dir)
            
            # Add archive info
            if self.config.MODIFY_HTML_FOR_LOCAL:
                self.add_archive_overlay(soup, url)
            
            # Save processed HTML
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            
            # Extract new URLs
            self.extract_urls_from_html(soup, url)
            
            self.stats['html_files'] += 1
            return True
            
        except Exception as e:
            print(f"❌ HTML processing failed: {e}")
            return False
    
    def update_html_links(self, soup, base_url, base_dir):
        """Update all links in HTML for local viewing"""
        
        # Update href attributes
        for tag in soup.find_all(['a', 'link']):
            if 'href' in tag.attrs:
                original = tag['href']
                new_url = self.convert_url_for_local(original, base_url, base_dir)
                if new_url:
                    tag['href'] = new_url
        
        # Update src attributes
        for tag in soup.find_all(['img', 'script', 'iframe', 'embed', 'source', 'audio', 'video']):
            if 'src' in tag.attrs:
                original = tag['src']
                new_url = self.convert_url_for_local(original, base_url, base_dir)
                if new_url:
                    tag['src'] = new_url
        
        # Update srcset
        for tag in soup.find_all(['img', 'source']):
            if 'srcset' in tag.attrs:
                srcset = tag['srcset']
                parts = [p.strip() for p in srcset.split(',')]
                new_parts = []
                
                for part in parts:
                    if ' ' in part:
                        url, descriptor = part.rsplit(' ', 1)
                        url = url.strip()
                        new_url = self.convert_url_for_local(url, base_url, base_dir)
                        if new_url:
                            new_parts.append(f'{new_url} {descriptor}')
                        else:
                            new_parts.append(part)
                    else:
                        new_url = self.convert_url_for_local(part, base_url, base_dir)
                        if new_url:
                            new_parts.append(new_url)
                        else:
                            new_parts.append(part)
                
                tag['srcset'] = ', '.join(new_parts)
        
        # Update inline CSS
        for tag in soup.find_all(style=True):
            style = tag['style']
            updated = self.update_css_urls(style, base_url, base_dir)
            tag['style'] = updated
    
    def convert_url_for_local(self, url, base_url, base_dir):
        """Convert URL for local viewing"""
        if not url or url.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'sms:')):
            return url
        
        if url.startswith('data:'):
            # Handle large data URLs
            if len(url) > 5000:
                try:
                    # Extract and save
                    if ';base64,' in url:
                        header, data = url.split(';base64,', 1)
                        mime = header[5:]
                        ext = mimetypes.guess_extension(mime.split(';')[0]) or '.bin'
                        
                        hash_str = hashlib.md5(data.encode()).hexdigest()[:8]
                        filename = f"data_{hash_str}{ext}"
                        filepath = self.assets_dir / filename
                        
                        import base64
                        with open(filepath, 'wb') as f:
                            f.write(base64.b64decode(data))
                        
                        rel_path = os.path.relpath(filepath, base_dir)
                        self.url_to_local[url] = filepath
                        return rel_path.replace('\\', '/')
                except:
                    pass
            return url
        
        # Normalize URL
        absolute_url = self.normalize_url(url, base_url)
        if not absolute_url:
            return url
        
        # Check if same domain
        parsed = urlparse(absolute_url)
        if parsed.netloc and parsed.netloc != self.base_domain:
            return absolute_url  # Keep external URLs as-is
        
        # Check robots.txt
        if not self.is_allowed_by_robots(absolute_url):
            return url
        
        # Queue for download if not already
        if absolute_url not in self.visited_urls and absolute_url not in self.urls_to_visit:
            self.urls_to_visit.add(absolute_url)
        
        # Return local path if already downloaded
        if absolute_url in self.url_to_local:
            local_path = self.url_to_local[absolute_url]
            rel_path = os.path.relpath(local_path, base_dir)
            return rel_path.replace('\\', '/')
        
        return url
    
    def update_css_urls(self, css_content, base_url, base_dir):
        """Update URLs in CSS"""
        def replace_url(match):
            url_content = match.group(1) or match.group(2)
            
            # Remove quotes
            if url_content.startswith(('"', "'")):
                quote_char = url_content[0]
                url = url_content.strip(quote_char)
            else:
                url = url_content
            
            # Convert URL
            new_url = self.convert_url_for_local(url, base_url, base_dir)
            
            if new_url:
                if url_content.startswith(('"', "'")):
                    return f'url({quote_char}{new_url}{quote_char})'
                else:
                    return f'url({new_url})'
            
            return match.group(0)
        
        pattern = r'url\(\s*(["\']?)(.*?)\1\s*\)'
        return re.sub(pattern, replace_url, css_content, flags=re.IGNORECASE)
    
    def add_archive_overlay(self, soup, original_url):
        """Add archive information overlay"""
        if not soup.body:
            return
        
        # Create overlay div
        overlay = soup.new_tag('div')
        overlay['id'] = 'web-archive-overlay'
        overlay['style'] = '''
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 12px;
            z-index: 999999;
            max-width: 300px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        '''
        
        # Content
        content = f'''
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div style="background: #4F46E5; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px;">
                📁
            </div>
            <div>
                <div style="font-weight: bold; font-size: 14px;">Web Archive</div>
                <div style="opacity: 0.8; font-size: 11px;">Local Copy</div>
            </div>
        </div>
        <div style="border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 8px;">
            <div style="margin-bottom: 4px; display: flex; justify-content: space-between;">
                <span>Original URL:</span>
            </div>
            <div style="background: rgba(255, 255, 255, 0.1); padding: 6px 8px; border-radius: 4px; font-size: 11px; margin-bottom: 8px; word-break: break-all;">
                {original_url[:60]}{'...' if len(original_url) > 60 else ''}
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
                <a href="{original_url}" target="_blank" style="background: #4F46E5; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 11px; flex: 1; text-align: center;">
                    🔗 View Original
                </a>
                <a href="/" style="background: rgba(255, 255, 255, 0.1); color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 11px; flex: 1; text-align: center;">
                    🏠 Archive Home
                </a>
            </div>
        </div>
        '''
        
        overlay.append(BeautifulSoup(content, 'html.parser'))
        soup.body.append(overlay)
        
        # Add toggle button
        toggle = soup.new_tag('button')
        toggle['onclick'] = "document.getElementById('web-archive-overlay').style.display='none'"
        toggle['style'] = '''
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #4F46E5;
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 1000000;
            font-size: 20px;
            display: none;
        '''
        toggle.string = '×'
        soup.body.append(toggle)
        
        # Add CSS for hover effect
        style = soup.new_tag('style')
        style.string = '''
            #web-archive-overlay:hover {
                transform: translateY(-2px);
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
                transition: all 0.3s ease;
            }
            #web-archive-overlay a:hover {
                opacity: 0.9;
            }
        '''
        soup.head.append(style)
    
    def extract_urls_from_html(self, soup, base_url):
        """Extract URLs from HTML for crawling"""
        # Extract from href
        for tag in soup.find_all(['a', 'link', 'area']):
            if 'href' in tag.attrs:
                url = tag['href']
                absolute = self.normalize_url(url, base_url)
                if absolute and self.should_crawl_url(absolute):
                    self.urls_to_visit.add(absolute)
        
        # Extract from src
        for tag in soup.find_all(['img', 'script', 'iframe', 'embed', 'source', 'audio', 'video']):
            if 'src' in tag.attrs:
                url = tag['src']
                absolute = self.normalize_url(url, base_url)
                if absolute and self.should_crawl_url(absolute):
                    self.urls_to_visit.add(absolute)
        
        # Extract from srcset
        for tag in soup.find_all(['img', 'source']):
            if 'srcset' in tag.attrs:
                srcset = tag['srcset']
                for part in srcset.split(','):
                    if ' ' in part:
                        url = part.rsplit(' ', 1)[0].strip()
                        absolute = self.normalize_url(url, base_url)
                        if absolute and self.should_crawl_url(absolute):
                            self.urls_to_visit.add(absolute)
    
    def should_crawl_url(self, url):
        """Determine if URL should be crawled"""
        if url in self.visited_urls:
            return False
        
        if url in self.urls_to_visit:
            return False
        
        # Check domain
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != self.base_domain:
            return False
        
        # Check robots.txt
        if not self.is_allowed_by_robots(url):
            return False
        
        # Check limits
        if self.stats['total_pages'] >= self.config.MAX_PAGES:
            return False
        
        if self.stats['total_size'] >= self.config.MAX_TOTAL_SIZE:
            return False
        
        return True
    
    # ============================================================================
    # MAIN ARCHIVE FUNCTION
    # ============================================================================
    
    def archive_website(self, max_pages=None, max_depth=None):
        """Main archive function"""
        if max_pages:
            self.config.MAX_PAGES = max_pages
        
        print(f"\n{'='*80}")
        print(f"🚀 STARTING WEB ARCHIVE")
        print(f"{'='*80}")
        print(f"🌐 URL: {self.base_url}")
        print(f"📁 Local: {self.output_dir}")
        if self.drive_path:
            print(f"📁 Drive: {self.drive_path}")
        print(f"📊 Limits: {self.config.MAX_PAGES} pages, {self.config.MAX_TOTAL_SIZE/(1024*1024*1024):.1f} GB")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        try:
            # Main crawl loop
            with tqdm(total=self.config.MAX_PAGES, desc="🌐 Archiving") as pbar:
                while self.urls_to_visit and self.stats['total_pages'] < self.config.MAX_PAGES:
                    url = self.urls_to_visit.pop()
                    
                    if url in self.visited_urls:
                        continue
                    
                    self.visited_urls.add(url)
                    
                    # Download the file
                    success, local_path, content_type, size = self.download_with_progress(url)
                    
                    if success and local_path:
                        # Check if it's HTML
                        if content_type and 'html' in content_type.lower():
                            # Process HTML
                            self.process_html_file(url, local_path)
                            self.stats['total_pages'] += 1
                            pbar.update(1)
                            pbar.set_postfix({
                                'Pages': self.stats['total_pages'],
                                'Files': self.stats['total_files'],
                                'Size': f"{self.stats['total_size']/(1024*1024):.1f}MB"
                            })
                    
                    # Small delay to be polite
                    time.sleep(0.1)
            
            # Create archive index
            self.create_archive_index()
            
            # Create local server
            if self.config.CREATE_LOCAL_SERVER:
                self.create_local_server()
            
            # Save to Google Drive
            if self.config.SAVE_TO_DRIVE and self.drive_path:
                self.save_to_drive()
            
            # Create ZIP archive
            if self.config.COMPRESS_ARCHIVE:
                self.create_zip_archive()
            
            # Generate report
            report = self.generate_archive_report()
            
            elapsed = time.time() - start_time
            
            print(f"\n{'='*80}")
            print(f"✅ ARCHIVE COMPLETE")
            print(f"{'='*80}")
            print(f"⏱️  Time: {elapsed:.1f}s")
            print(f"📄 Pages: {self.stats['html_files']}")
            print(f"📦 Files: {self.stats['total_files']}")
            print(f"💾 Size: {self.stats['total_size']/(1024*1024):.1f} MB")
            print(f"📁 Local: {self.output_dir}")
            if self.drive_path:
                print(f"☁️  Drive: {self.drive_path}")
            print(f"{'='*80}")
            
            return report
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Archive interrupted by user")
            self.create_archive_index()
            return self.generate_archive_report()
        
        except Exception as e:
            print(f"\n❌ Archive failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ============================================================================
    # GOOGLE DRIVE INTEGRATION
    # ============================================================================
    
    def save_to_drive(self, delete_local=False):
        """Save archive to Google Drive"""
        if not self.drive_path:
            print("❌ No Drive path configured")
            return False
        
        print(f"\n📤 Saving to Google Drive...")
        print(f"📁 Source: {self.output_dir}")
        print(f"📁 Destination: {self.drive_path}")
        
        try:
            # Copy to Drive
            success = self.drive_manager.copy_to_drive(self.output_dir, self.drive_path)
            
            if success:
                print(f"✅ Successfully saved to Google Drive!")
                
                # Create Drive URL (for display)
                drive_url = f"https://drive.google.com/drive/folders/{self.drive_path.name}"
                print(f"🔗 Access at: {drive_url}")
                
                # Optionally delete local copy
                if delete_local:
                    shutil.rmtree(self.output_dir)
                    print(f"🗑️  Deleted local copy")
                
                return True
            else:
                print("❌ Failed to save to Google Drive")
                return False
                
        except Exception as e:
            print(f"❌ Drive save error: {e}")
            return False
    
    def sync_to_drive(self, interval=60):
        """Sync to Drive at intervals during archive"""
        if not self.drive_path:
            return
        
        print(f"🔄 Setting up Drive sync every {interval}s...")
        
        # This would be implemented with threading in a full app
        # For Colab, we'll do a final sync
        pass
    
    # ============================================================================
    # ARCHIVE MANAGEMENT
    # ============================================================================
    
    def create_archive_index(self):
        """Create beautiful index.html for the archive"""
        index_path = self.output_dir / 'index.html'
        
        # Get file tree
        file_tree = self.generate_file_tree()
        
        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📁 Web Archive: {self.base_domain}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --primary: #4F46E5;
            --primary-dark: #4338CA;
            --secondary: #10B981;
            --background: #F8FAFC;
            --surface: #FFFFFF;
            --text: #1E293B;
            --text-light: #64748B;
            --border: #E2E8F0;
            --shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            --radius: 12px;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--background);
            color: var(--text);
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 60px 40px;
            border-radius: var(--radius);
            margin-bottom: 40px;
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }}
        
        header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 100%;
            height: 200%;
            background: rgba(255, 255, 255, 0.1);
            transform: rotate(30deg);
        }}
        
        .header-content {{
            position: relative;
            z-index: 1;
        }}
        
        h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        
        .domain {{
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 20px;
            border-radius: 50px;
            font-size: 0.8em;
            backdrop-filter: blur(10px);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }}
        
        .stat-card {{
            background: var(--surface);
            padding: 25px;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        }}
        
        .stat-icon {{
            font-size: 2.5em;
            margin-bottom: 15px;
            color: var(--primary);
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: var(--text);
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: var(--text-light);
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .file-section {{
            background: var(--surface);
            border-radius: var(--radius);
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: var(--shadow);
        }}
        
        .file-tree {{
            font-family: 'Courier New', monospace;
            background: #1E293B;
            color: #E2E8F0;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
        }}
        
        .actions {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin: 40px 0;
        }}
        
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: var(--primary);
            color: white;
            padding: 15px 30px;
            border-radius: var(--radius);
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
            font-size: 1em;
        }}
        
        .btn:hover {{
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(79, 70, 229, 0.3);
        }}
        
        .btn-secondary {{
            background: var(--text-light);
        }}
        
        .btn-success {{
            background: var(--secondary);
        }}
        
        .drive-info {{
            background: linear-gradient(135deg, #1A73E8, #34A853);
            color: white;
            padding: 25px;
            border-radius: var(--radius);
            margin: 40px 0;
            box-shadow: var(--shadow);
        }}
        
        footer {{
            text-align: center;
            padding: 40px 0;
            color: var(--text-light);
            border-top: 1px solid var(--border);
            margin-top: 60px;
        }}
        
        @media (max-width: 768px) {{
            h1 {{ font-size: 2em; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
            .actions {{ flex-direction: column; }}
            .btn {{ width: 100%; justify-content: center; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>
                    <i class="fas fa-archive"></i>
                    Web Archive
                    <span class="domain">{self.base_domain}</span>
                </h1>
                <p>Complete local copy archived on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-file-alt"></i></div>
                <div class="stat-number">{self.stats['html_files']}</div>
                <div class="stat-label">HTML Pages</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-file-code"></i></div>
                <div class="stat-number">{self.stats['css_files'] + self.stats['js_files']}</div>
                <div class="stat-label">Code Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-images"></i></div>
                <div class="stat-number">{self.stats['images']}</div>
                <div class="stat-label">Images</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-database"></i></div>
                <div class="stat-number">{self.stats['total_size']/(1024*1024):.1f} MB</div>
                <div class="stat-label">Total Size</div>
            </div>
        </div>
        
        <div class="file-section">
            <h2><i class="fas fa-folder-open"></i> Archive Contents</h2>
            <div class="file-tree">
                {file_tree}
            </div>
        </div>
        
        <div class="actions">
            <a href="{self.find_main_page()}" class="btn">
                <i class="fas fa-external-link-alt"></i>
                Open Main Page
            </a>
            <a href="{self.original_url}" target="_blank" class="btn btn-secondary">
                <i class="fas fa-globe"></i>
                View Original Site
            </a>
            <button onclick="downloadZip()" class="btn btn-success">
                <i class="fas fa-file-archive"></i>
                Download ZIP
            </button>
        </div>
        
        {self.generate_drive_section()}
        
        <footer>
            <p>Created with Web Archiver Pro • For educational purposes only</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                <i class="fas fa-exclamation-triangle"></i>
                Respect copyright laws. Only archive websites you own or have permission to archive.
            </p>
        </footer>
    </div>
    
    <script>
        function downloadZip() {{
            alert('ZIP download would start here. In Colab, use files.download()');
        }}
        
        // File tree toggle
        document.querySelectorAll('.folder').forEach(folder => {{
            folder.addEventListener('click', function() {{
                this.classList.toggle('collapsed');
            }});
        }});
    </script>
</body>
</html>'''
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        print(f"✅ Created archive index: {index_path}")
        return index_path
    
    def generate_file_tree(self, max_depth=3):
        """Generate file tree for display"""
        tree_lines = []
        
        def walk_dir(path, prefix="", depth=0):
            if depth > max_depth:
                return
            
            try:
                items = sorted(path.iterdir())
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    
                    if item.is_dir():
                        tree_lines.append(f"{prefix}{'└── ' if is_last else '├── '}📁 {item.name}/")
                        extension = "    " if is_last else "│   "
                        walk_dir(item, prefix + extension, depth + 1)
                    else:
                        size = item.stat().st_size
                        size_str = f" ({size/1024:.1f} KB)" if size > 0 else ""
                        icon = self.get_file_icon(item.name)
                        tree_lines.append(f"{prefix}{'└── ' if is_last else '├── '}{icon} {item.name}{size_str}")
            except:
                pass
        
        walk_dir(self.output_dir)
        return '\n'.join(tree_lines[:50])  # Limit to 50 lines
    
    def get_file_icon(self, filename):
        """Get icon for file type"""
        ext = os.path.splitext(filename)[1].lower()
        
        icons = {
            '.html': '🌐',
            '.css': '🎨',
            '.js': '📜',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.png': '🖼️',
            '.gif': '🖼️',
            '.svg': '🖼️',
            '.pdf': '📄',
            '.zip': '📦',
            '.mp4': '🎥',
            '.mp3': '🎵',
            '.ttf': '🔤',
            '.woff': '🔤',
            '.woff2': '🔤',
        }
        
        return icons.get(ext, '📄')
    
    def generate_drive_section(self):
        """Generate Google Drive section for index"""
        if not self.drive_path:
            return ""
        
        return f'''
        <div class="drive-info">
            <h3><i class="fas fa-cloud"></i> Google Drive Backup</h3>
            <p>This archive has been automatically backed up to your Google Drive.</p>
            <p><strong>Location:</strong> {self.drive_path}</p>
            <p><i class="fas fa-info-circle"></i> Access your files from any device via Google Drive</p>
        </div>
        '''
    
    def find_main_page(self):
        """Find the main page of the archive"""
        possible_names = ['index.html', 'home.html', 'default.html', 'main.html']
        
        for name in possible_names:
            if (self.output_dir / name).exists():
                return name
        
        # Search for any HTML file
        html_files = list(self.output_dir.rglob('*.html'))
        if html_files:
            return html_files[0].relative_to(self.output_dir)
        
        return '#'
    
    def create_local_server(self):
        """Create simple HTTP server script"""
        server_script = self.output_dir / 'serve.py'
        
        server_code = '''#!/usr/bin/env python3
"""
Web Archive Local Server
Usage: python serve.py
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080
DIRECTORY = str(Path(__file__).parent)

class ArchiveRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        # Custom log format
        pass
    
    def end_headers(self):
        # Add headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def main():
    os.chdir(DIRECTORY)
    
    with socketserver.TCPServer(("", PORT), ArchiveRequestHandler) as httpd:
        print("🌐 Web Archive Local Server")
        print("=" * 50)
        print(f"📁 Serving: {DIRECTORY}")
        print(f"🔗 URL: http://localhost:{PORT}")
        print("=" * 50)
        print("🛑 Press Ctrl+C to stop")
        
        # Try to open browser
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
'''
        
        with open(server_script, 'w', encoding='utf-8') as f:
            f.write(server_code)
        
        # Make executable
        os.chmod(server_script, 0o755)
        
        print(f"✅ Created local server script: {server_script}")
    
    def create_zip_archive(self):
        """Create ZIP archive of the website"""
        zip_path = Path(f'/content/{self.output_dir.name}.zip')
        
        print(f"📦 Creating ZIP archive: {zip_path}")
        
        try:
            shutil.make_archive(str(zip_path).replace('.zip', ''), 'zip', self.output_dir)
            
            size = zip_path.stat().st_size / (1024*1024)
            print(f"✅ ZIP created: {zip_path.name} ({size:.1f} MB)")
            
            return zip_path
            
        except Exception as e:
            print(f"❌ ZIP creation failed: {e}")
            return None
    
    def generate_archive_report(self):
        """Generate detailed archive report"""
        report_path = self.output_dir / 'archive_report.json'
        
        report = {
            'metadata': {
                'original_url': self.original_url,
                'base_domain': self.base_domain,
                'archive_date': datetime.now().isoformat(),
                'output_directory': str(self.output_dir),
                'drive_directory': str(self.drive_path) if self.drive_path else None,
                'user_agent': self.config.USER_AGENT,
            },
            'statistics': self.stats.copy(),
            'configuration': {
                'max_pages': self.config.MAX_PAGES,
                'max_file_size': self.config.MAX_FILE_SIZE,
                'max_total_size': self.config.MAX_TOTAL_SIZE,
                'respect_robots': self.config.RESPECT_ROBOTS,
                'save_to_drive': self.config.SAVE_TO_DRIVE,
            },
            'files': {
                'html_files': self.stats['html_files'],
                'css_files': self.stats['css_files'],
                'js_files': self.stats['js_files'],
                'images': self.stats['images'],
                'fonts': self.stats['fonts'],
                'other_files': self.stats['other_files'],
                'total_files': self.stats['total_files'],
                'total_size_bytes': self.stats['total_size'],
                'total_size_mb': self.stats['total_size'] / (1024 * 1024),
            },
            'processing': {
                'visited_urls': len(self.visited_urls),
                'failed_downloads': self.stats['failed_downloads'],
                'urls_to_visit': len(self.urls_to_visit),
            }
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Archive report saved: {report_path}")
        return report

# @title =========================================
# @title 🎮 INTERACTIVE ARCHIVER GUI
# @title =========================================

from IPython.display import display, HTML, clear_output
import ipywidgets as widgets

def create_archiver_gui():
    """Create interactive GUI for the archiver"""
    
    # Title
    display(HTML("""
    <div style="background: linear-gradient(135deg, #4F46E5, #7C3AED); 
                color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px;">
        <h1 style="margin: 0; display: flex; align-items: center; gap: 15px;">
            <span>🌐</span>
            <span>Web Archiver Pro</span>
        </h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Complete website archiving with Google Drive integration</p>
    </div>
    """))
    
    # URL input
    url_input = widgets.Text(
        value='',
        placeholder='https://example.com',
        description='🌐 URL:',
        layout=widgets.Layout(width='85%'),
        style={'description_width': 'initial'}
    )
    
    # Configuration
    pages_slider = widgets.IntSlider(
        value=50,
        min=1,
        max=200,
        step=1,
        description='📄 Max Pages:',
        continuous_update=False,
        layout=widgets.Layout(width='80%')
    )
    
    drive_checkbox = widgets.Checkbox(
        value=True,
        description='💾 Save to Google Drive',
        indent=False,
        layout=widgets.Layout(width='250px')
    )
    
    compress_checkbox = widgets.Checkbox(
        value=True,
        description='📦 Create ZIP',
        indent=False,
        layout=widgets.Layout(width='200px')
    )
    
    folder_input = widgets.Text(
        value='',
        placeholder='my_website_backup (optional)',
        description='📁 Folder:',
        layout=widgets.Layout(width='70%')
    )
    
    # Buttons
    start_btn = widgets.Button(
        description='🚀 Start Archive',
        button_style='success',
        layout=widgets.Layout(width='200px', height='45px'),
        icon='play'
    )
    
    drive_btn = widgets.Button(
        description='📤 Save to Drive',
        button_style='info',
        layout=widgets.Layout(width='180px', height='40px'),
        icon='cloud-upload',
        disabled=True
    )
    
    download_btn = widgets.Button(
        description='📥 Download ZIP',
        button_style='warning',
        layout=widgets.Layout(width='180px', height='40px'),
        icon='download',
        disabled=True
    )
    
    view_btn = widgets.Button(
        description='👁️ View Archive',
        button_style='primary',
        layout=widgets.Layout(width='180px', height='40px'),
        icon='eye',
        disabled=True
    )
    
    # Progress bar
    progress_bar = widgets.FloatProgress(
        value=0,
        min=0,
        max=100,
        description='Progress:',
        bar_style='info',
        style={'bar_color': '#4F46E5'},
        layout=widgets.Layout(width='85%', visibility='hidden')
    )
    
    # Status output
    status_output = widgets.Output()
    
    # Archive instance storage
    archive_instance = None
    archive_dir = None
    zip_path = None
    
    def on_start_click(b):
        nonlocal archive_instance, archive_dir
        
        with status_output:
            clear_output(wait=True)
            
            url = url_input.value.strip()
            if not url:
                print("❌ Please enter a URL")
                return
            
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            print("🚀 Initializing Web Archiver Pro...")
            print(f"🌐 URL: {url}")
            print(f"📊 Max pages: {pages_slider.value}")
            print(f"💾 Save to Drive: {'Yes' if drive_checkbox.value else 'No'}")
            print(f"📦 Create ZIP: {'Yes' if compress_checkbox.value else 'No'}")
            print("-" * 60)
            
            # Show progress bar
            progress_bar.layout.visibility = 'visible'
            progress_bar.value = 10
            
            try:
                # Create configuration
                config = Config()
                config.MAX_PAGES = pages_slider.value
                config.SAVE_TO_DRIVE = drive_checkbox.value
                config.COMPRESS_ARCHIVE = compress_checkbox.value
                
                # Create archiver
                archive_instance = AdvancedWebArchiver(
                    url,
                    output_dir=None,  # Auto-generate
                    config=config,
                    auto_mount_drive=True
                )
                
                # Update folder name if provided
                if folder_input.value.strip():
                    import shutil
                    new_dir = Path(f'/content/{folder_input.value.strip()}')
                    if archive_instance.output_dir != new_dir:
                        shutil.move(archive_instance.output_dir, new_dir)
                        archive_instance.output_dir = new_dir
                
                progress_bar.value = 30
                
                # Start archive
                print("\n📡 Starting archive process...")
                report = archive_instance.archive_website()
                
                if report:
                    progress_bar.value = 100
                    archive_dir = archive_instance.output_dir
                    
                    print(f"\n✅ Archive complete!")
                    print(f"📁 Local directory: {archive_dir}")
                    
                    if archive_instance.drive_path:
                        print(f"☁️  Drive directory: {archive_instance.drive_path}")
                    
                    # Enable action buttons
                    drive_btn.disabled = False
                    download_btn.disabled = False
                    view_btn.disabled = False
                    
                    # Store ZIP path if created
                    if config.COMPRESS_ARCHIVE:
                        zip_name = f'{archive_dir.name}.zip'
                        nonlocal zip_path
                        zip_path = Path(f'/content/{zip_name}')
                    
                    # Hide progress bar
                    progress_bar.layout.visibility = 'hidden'
                    
                else:
                    print("❌ Archive failed")
                    progress_bar.layout.visibility = 'hidden'
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:200]}")
                progress_bar.layout.visibility = 'hidden'
    
    def on_drive_click(b):
        with status_output:
            clear_output(wait=True)
            
            if archive_instance and archive_instance.drive_path:
                print("📤 Saving to Google Drive...")
                
                try:
                    success = archive_instance.save_to_drive(delete_local=False)
                    
                    if success:
                        print(f"✅ Successfully saved to Google Drive!")
                        print(f"📁 Location: {archive_instance.drive_path}")
                    else:
                        print("❌ Failed to save to Google Drive")
                        
                except Exception as e:
                    print(f"❌ Drive save error: {e}")
            else:
                print("❌ No archive found or Drive not configured")
    
    def on_download_click(b):
        with status_output:
            clear_output(wait=True)
            
            if zip_path and zip_path.exists():
                print(f"📥 Downloading ZIP archive...")
                print(f"📦 File: {zip_path.name}")
                print(f"💾 Size: {zip_path.stat().st_size/(1024*1024):.1f} MB")
                
                try:
                    files.download(str(zip_path))
                    print("✅ Download started!")
                except Exception as e:
                    print(f"❌ Download error: {e}")
            else:
                print("❌ ZIP file not found. Creating one now...")
                
                try:
                    if archive_dir:
                        zip_file = archive_instance.create_zip_archive()
                        if zip_file:
                            files.download(str(zip_file))
                    else:
                        print("❌ No archive directory found")
                except Exception as e:
                    print(f"❌ Error: {e}")
    
    def on_view_click(b):
        with status_output:
            clear_output(wait=True)
            
            if archive_dir:
                print("👁️ Viewing archive...")
                print(f"📁 Directory: {archive_dir}")
                
                # Show directory structure
                print("\n📂 Directory Structure:")
                print("-" * 50)
                !cd "{archive_dir}" && tree -L 3 || ls -la "{archive_dir}"
                print("-" * 50)
                
                # Show index.html path
                index_path = archive_dir / 'index.html'
                if index_path.exists():
                    print(f"\n📄 Open index.html to view the archive")
                    print(f"🔗 Local path: {index_path}")
                    
                    # Create HTML preview
                    with open(index_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Show first 1000 chars
                    preview = html_content[:1000] + ('...' if len(html_content) > 1000 else '')
                    print(f"\n📋 Preview (first 1000 chars):")
                    print("-" * 50)
                    print(preview)
                    print("-" * 50)
                else:
                    print("❌ index.html not found")
                    
                print(f"\n💡 To serve locally, run:")
                print(f"   cd {archive_dir}")
                print(f"   python serve.py")
                print(f"   Then open http://localhost:8080")
            else:
                print("❌ No archive found")
    
    # Connect buttons
    start_btn.on_click(on_start_click)
    drive_btn.on_click(on_drive_click)
    download_btn.on_click(on_download_click)
    view_btn.on_click(on_view_click)
    
    # Create layout
    config_section = widgets.VBox([
        widgets.HTML("<h3>⚙️ Configuration</h3>"),
        widgets.HBox([url_input]),
        widgets.HBox([pages_slider]),
        widgets.HBox([drive_checkbox, compress_checkbox]),
        widgets.HBox([folder_input]),
    ])
    
    action_section = widgets.VBox([
        widgets.HTML("<h3>🎯 Actions</h3>"),
        widgets.HBox([start_btn]),
        widgets.HBox([drive_btn, download_btn, view_btn]),
        progress_bar,
    ])
    
    # Display everything
    display(config_section)
    display(action_section)
    display(status_output)

# @title =========================================
# @title 🚀 QUICK FUNCTIONS
# @title =========================================

def quick_archive(url, max_pages=50, save_to_drive=True, create_zip=True):
    """
    Quick archive function
    Example: quick_archive('https://example.com', 30)
    """
    print(f"🚀 Quick archive: {url}")
    
    config = Config()
    config.MAX_PAGES = max_pages
    config.SAVE_TO_DRIVE = save_to_drive
    config.COMPRESS_ARCHIVE = create_zip
    
    archiver = AdvancedWebArchiver(url, config=config)
    report = archiver.archive_website()
    
    if report:
        print(f"\n✅ Archive complete!")
        print(f"📁 Local: {archiver.output_dir}")
        
        if archiver.drive_path:
            print(f"☁️  Drive: {archiver.drive_path}")
        
        # Offer ZIP download
        if create_zip:
            zip_file = archiver.create_zip_archive()
            if zip_file:
                print(f"📦 ZIP: {zip_file}")
                return {
                    'archiver': archiver,
                    'report': report,
                    'local_dir': archiver.output_dir,
                    'drive_dir': archiver.drive_path,
                    'zip_file': zip_file
                }
    
    return None

def archive_and_download(url, max_pages=30):
    """Archive and download immediately"""
    result = quick_archive(url, max_pages, save_to_drive=False, create_zip=True)
    
    if result and 'zip_file' in result:
        print(f"\n📥 Downloading ZIP...")
        files.download(str(result['zip_file']))
    
    return result

def archive_to_drive_only(url, max_pages=100):
    """Archive directly to Google Drive"""
    print(f"📁 Archiving to Google Drive: {url}")
    
    config = Config()
    config.MAX_PAGES = max_pages
    config.SAVE_TO_DRIVE = True
    config.COMPRESS_ARCHIVE = False  # Don't create ZIP
    
    archiver = AdvancedWebArchiver(url, config=config)
    report = archiver.archive_website()
    
    if report and archiver.drive_path:
        print(f"✅ Archived to Google Drive: {archiver.drive_path}")
        return archiver.drive_path
    
    return None

# @title =========================================
# @title 📝 EXAMPLES & USAGE
# @title =========================================

# @markdown ### **Example 1: Interactive GUI**
print("Run this to open the interactive archiver:")
print("create_archiver_gui()")

# @markdown ### **Example 2: Quick Archive**
example_code = '''
# Simple archive
result = quick_archive("https://example.com", max_pages=30)

# Archive with Drive backup
result = quick_archive("https://example.com", max_pages=50, save_to_drive=True)

# Archive and download ZIP
result = archive_and_download("https://example.com", max_pages=20)

# Archive to Drive only
drive_path = archive_to_drive_only("https://example.com", max_pages=100)
'''

print(example_code)

# @markdown ### **Example 3: Advanced Usage**
advanced_code = '''
# Custom configuration
config = Config()
config.MAX_PAGES = 200
config.MAX_TOTAL_SIZE = 3 * 1024 * 1024 * 1024  # 3GB
config.SAVE_TO_DRIVE = True
config.COMPRESS_ARCHIVE = True

# Create archiver
archiver = AdvancedWebArchiver(
    "https://example.com",
    output_dir="/content/my_custom_backup",
    config=config
)

# Start archive
report = archiver.archive_website()

# Save to Drive
archiver.save_to_drive()

# Create and download ZIP
zip_file = archiver.create_zip_archive()
files.download(str(zip_file))
'''

print(advanced_code)

# @title =========================================
# @title ⚠️  LEGAL DISCLAIMER
# @title =========================================

disclaimer = HTML("""
<div style="background: linear-gradient(135deg, #F59E0B, #D97706); 
            color: white; padding: 25px; border-radius: 15px; margin: 30px 0;
            border: 2px solid #92400E;">
    <h3 style="margin-top: 0; display: flex; align-items: center; gap: 10px;">
        <span>⚠️</span>
        <span>LEGAL DISCLAIMER</span>
    </h3>
    <p style="margin-bottom: 10px;">
        This tool is for <strong>EDUCATIONAL PURPOSES ONLY</strong>.
    </p>
    <ul style="margin: 0; padding-left: 20px;">
        <li>Only archive websites you <strong>own</strong> or have <strong>explicit permission</strong> to archive</li>
        <li><strong>Respect copyright laws</strong> and website Terms of Service</li>
        <li>Check <code>robots.txt</code> before archiving</li>
        <li>Never archive personal, private, or sensitive information</li>
        <li>The developers are <strong>not responsible</strong> for misuse</li>
    </ul>
    <p style="margin-top: 15px; font-style: italic;">
        By using this tool, you agree to use it responsibly and legally.
    </p>
</div>
""")

display(disclaimer)

# @title =========================================
# @title 🎯 READY TO START
# @title =========================================

print("\n" + "="*70)
print("✅ WEB ARCHIVER PRO READY!")
print("="*70)
print("\nChoose an option:")
print("1. create_archiver_gui() - Interactive interface with Drive")
print("2. quick_archive(url) - Simple one-line archive")
print("3. archive_and_download(url) - Archive and download ZIP")
print("4. archive_to_drive_only(url) - Archive directly to Drive")
print("\nExample: quick_archive('https://example.com', 30)")

# @title =========================================
# @title 🎮 LAUNCH INTERACTIVE ARCHIVER
# @title =========================================

print("\n📱 Launching interactive archiver...")
print("="*70)

create_archiver_gui()
