!pip uninstall -y youtube-search-python httpx
!pip install httpx==0.23.0
!pip install youtube-search-python
from youtubesearchpython import VideosSearch

def get_artist_links_no_api(artist_name, limit=15):
    print(f"Searching YouTube for: {artist_name}...")

    # We search for the artist name + "official music video" for better accuracy
    query = f"{artist_name} official music video"
    video_search = VideosSearch(query, limit=limit)

    results = video_search.result()

    if not results['result']:
        print("No videos found.")
        return

    print(f"\nTop {limit} videos for {artist_name}:")
    print("="*40)

    for video in results['result']:
        title = video['title']
        link = video['link']
        duration = video['duration']
        views = video['viewCount']['short']

        print(f"🎥 {title}")
        print(f"   Link: {link}")
        print(f"   Duration: {duration} | Views: {views}")
        print("-" * 40)

# User Input
artist = input("Enter artist name: ")
get_artist_links_no_api(artist)
