!pip install yt-dlp
import os
import yt_dlp
import time
from google.colab import drive
from IPython.display import clear_output

# 1. INITIALIZE & MOUNT DRIVE
print("🚀 Initializing system...")
drive.mount('/content/drive', force_remount=False)

def run_pro_downloader():
    save_path = '/content/drive/MyDrive/YouTube_Downloads'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    while True:
        clear_output(wait=True)
        print("🎵 " + "═"*35 + " 🎵")
        print("   YOUTUBE PRO MP3 DOWNLOADER")
        print("🎵 " + "═"*35 + " 🎵")
        print(f"📂 Saving to: {save_path}")
        print("🏷️  Feature: Auto-Metadata & Progress Bar Enabled")
        print("⎯" * 39)
        
        print("💡 Paste YouTube URL(s) below.")
        print("📝 (Separate with commas, or type 'exit' to stop)")
        
        time.sleep(0.5) 
        user_input = input("\n🔗 URL: ").strip()

        if user_input.lower() in ['exit', 'quit', 'stop', '']:
            if user_input == '': continue
            print("\n👋 See you later! Drive folder is updated.")
            break

        urls = [url.strip() for url in user_input.split(',')]

        # yt-dlp Configuration with Metadata and Progress logic
        ydl_opts = {
            'format': 'bestaudio/best',
            # This part handles the MP3 conversion AND the metadata
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {
                    'key': 'FFmpegMetadata', # Adds Artist, Title, etc.
                    'add_metadata': True,
                }
            ],
            'outtmpl': f'{save_path}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'noprogress': False, # We want to see progress
        }

        print("\n⏳ Starting Batch...")
        for url in urls:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Fetch info first for a clean display
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown')
                    
                    print(f"\n📥 Downloading: {title}")
                    ydl.download([url])
                    print(f"✅ Finished & Tagged: {title}")
            except Exception as e:
                print(f"❌ Error with {url}")
                print(f"   Details: {str(e)[:100]}")

        print("\n✨ Batch Complete!")
        input("\n⌨️ Press Enter to clear screen and continue...")

if __name__ == "__main__":
    run_pro_downloader()
