# 1. Install the library
!pip install newsapi-python

from newsapi import NewsApiClient
from google.colab import output
from IPython.display import HTML
import html

# --- CONFIGURATION ---
API_KEY = 'b801be7055d1442ba441e7c1f7a853c5' 
newsapi = NewsApiClient(api_key=API_KEY)

def fetch_daily_news(category='general', query=None):
    try:
        if query:
            # Search for specific keywords
            response = newsapi.get_everything(q=query, language='en', sort_by='publishedAt', page_size=20)
        else:
            # Fetch top headlines by category
            response = newsapi.get_top_headlines(category=category, language='en', country='us')
            
        articles = response.get('articles', [])
        
        if not articles:
            return "<p style='text-align:center; padding:20px;'>No news found. Try a different search term!</p>"

        result_html = '<div style="display: grid; grid-template-columns: 1fr; gap: 15px;">'
        
        for art in articles:
            title = html.escape(art['title'] or "No Title")
            source = html.escape(art['source']['name'] or "Unknown Source")
            desc = html.escape(art['description'] or "No description available.")
            url = art['url']
            
            result_html += f'''
                <div style="background: white; padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <small style="color: #007bff; font-weight: bold; text-transform: uppercase;">{source}</small>
                    </div>
                    <h3 style="margin: 10px 0; color: #1a1a1a; line-height: 1.3;">{title}</h3>
                    <p style="color: #444; font-size: 0.95rem; margin-bottom: 15px;">{desc}</p>
                    <a href="{url}" target="_blank" style="color: white; background: #007bff; text-decoration: none; padding: 8px 15px; border-radius: 5px; font-size: 0.85rem; display: inline-block;">Read Full Article</a>
                </div>
            '''
        result_html += '</div>'
        return result_html
    except Exception as e:
        return f"<div style='color:red; padding:20px;'>Error: {str(e)}<br>Tip: Make sure your API key is active.</div>"

# Register callback for Colab
output.register_callback('notebook.fetch_news', fetch_daily_news)

# --- THE UI ---
display(HTML('''
    <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; background: #f4f7f9; border-radius: 20px; min-height: 400px;">
        <h1 style="text-align: center; color: #1a1a1a; margin-bottom: 5px;">📰 NewsHub Daily</h1>
        <p style="text-align: center; color: #666; margin-bottom: 25px;">Stay updated with the world's top stories</p>
        
        <div style="text-align: center; margin-bottom: 25px;">
            <input id="search_input" type="text" placeholder="Search for news (e.g. AI, NASA)..." 
                   style="padding: 12px 20px; width: 60%; border-radius: 25px; border: 1px solid #ddd; outline: none;">
            <button onclick="updateNews(null, document.getElementById('search_input').value)" 
                    style="padding: 12px 25px; border-radius: 25px; border: none; background: #1a1a1a; color: white; cursor: pointer; font-weight: bold;">Search</button>
        </div>

        <div style="text-align: center; margin-bottom: 30px; display: flex; justify-content: center; flex-wrap: wrap; gap: 10px;">
            <button onclick="updateNews('general')" style="padding: 8px 18px; border-radius: 15px; border: 1px solid #007bff; background: white; color: #007bff; cursor: pointer;">General</button>
            <button onclick="updateNews('technology')" style="padding: 8px 18px; border-radius: 15px; border: 1px solid #6c757d; background: white; color: #6c757d; cursor: pointer;">Tech</button>
            <button onclick="updateNews('business')" style="padding: 8px 18px; border-radius: 15px; border: 1px solid #28a745; background: white; color: #28a745; cursor: pointer;">Business</button>
            <button onclick="updateNews('science')" style="padding: 8px 18px; border-radius: 15px; border: 1px solid #17a2b8; background: white; color: #17a2b8; cursor: pointer;">Science</button>
            <button onclick="updateNews('sports')" style="padding: 8px 18px; border-radius: 15px; border: 1px solid #fd7e14; background: white; color: #fd7e14; cursor: pointer;">Sports</button>
        </div>
        
        <div id="news_status" style="text-align: center; color: #666; font-style: italic; margin-bottom: 10px;"></div>
        <div id="news_container"></div>
    </div>

    <script>
        async function updateNews(cat, query=null) {
            const container = document.getElementById('news_container');
            const status = document.getElementById('news_status');
            status.innerHTML = "📡 Syncing latest headlines...";
            
            // Clear search bar if clicking a category
            if(cat) document.getElementById('search_input').value = "";

            const html_result = await google.colab.kernel.invokeFunction('notebook.fetch_news', [cat, query], {});
            container.innerHTML = html_result.data['text/plain'];
            status.innerHTML = "";
        }
        // Load default news
        updateNews('general');
    </script>
'''))
