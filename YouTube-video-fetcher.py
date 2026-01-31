!pip install yt-dlp
import yt_dlp
from google.colab import output
import html

# --- 1. The Python Logic ---
def get_youtube_videos(channel_handle):
    if not channel_handle.startswith('@'):
        channel_handle = f'@{channel_handle}'
    
    url = f"https://www.youtube.com/{channel_handle}/videos"
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'force_generic_extractor': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('entries', [])
        except Exception as e:
            return [{"title": f"Error: {e}", "url": "#"}]

# --- 2. The Bridge between Python and Javascript ---
def handle_search(handle):
    videos = get_youtube_videos(handle)
    
    # Generate the HTML for the results
    result_html = ""
    for v in videos:
        title = html.escape(v.get('title', 'No Title'))
        v_url = v.get('url', '#')
        result_html += f'''
            <div style="background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 5px solid red;">
                <strong>{title}</strong><br>
                <a href="{v_url}" target="_blank" style="color: #065fd4; text-decoration: none;">View Video</a>
            </div>
        '''
    return result_html

# Register the function so Javascript can call it
output.register_callback('notebook.handle_search', handle_search)

# --- 3. The HTML/UI Interface ---
from IPython.display import HTML

ui = HTML('''
    <div style="font-family: sans-serif; background: #f9f9f9; padding: 20px; border-radius: 10px;">
        <h2 style="color: #ff0000;">YouTube Channel Lister</h2>
        <input id="handle_input" type="text" placeholder="Enter handle (e.g. NetworkChuck)" 
               style="padding: 10px; width: 60%; border-radius: 5px; border: 1px solid #ccc;">
        <button onclick="runSearch()" style="padding: 10px 20px; background: #ff0000; color: white; border: none; border-radius: 5px; cursor: pointer;">
            Fetch Videos
        </button>
        
        <div id="status" style="margin-top: 10px; color: #666;"></div>
        <div id="results_container" style="margin-top: 20px;"></div>
    </div>

    <script>
        async function runSearch() {
            const handle = document.getElementById('handle_input').value;
            const container = document.getElementById('results_container');
            const status = document.getElementById('status');
            
            status.innerHTML = "Fetching videos... this might take a few seconds.";
            container.innerHTML = "";
            
            // Call the Python function from Javascript
            const html_result = await google.colab.kernel.invokeFunction('notebook.handle_search', [handle], {});
            
            container.innerHTML = html_result.data['text/plain'];
            status.innerHTML = "";
        }
    </script>
''')

display(ui)
