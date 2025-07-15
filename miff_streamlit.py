import streamlit as st
import pandas as pd
import re
import json
import requests
from urllib.parse import quote_plus
from typing import List, Dict

# Page configuration
st.set_page_config(
    page_title="MIFF 2025 Film Browser",
    page_icon="🎬",
    layout="wide"
)

# Function to load and process the data
@st.cache_data
def load_miff_data():
    """
    Load and process MIFF data from local file
    """
    try:
        # Load the main data file
        df = pd.read_csv('miff_2025_complete.csv')
        
        # Display basic info about the loaded data
        st.sidebar.info(f"✅ Loaded {len(df)} records from miff_2025_complete.csv")
        
        return df
        
    except FileNotFoundError:
        st.error("❌ Could not find 'miff_2025_complete.csv' in the current directory.")
        st.info("Please make sure the file exists in the same folder as this script.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()

def parse_genres(genre_string):
    """Parse genre string into list"""
    if pd.isna(genre_string) or genre_string == '':
        return []
    return [g.strip() for g in str(genre_string).split(',')]

def parse_languages(language_string):
    """Parse language string into list"""
    if pd.isna(language_string) or language_string == '':
        return []
    return [l.strip() for l in str(language_string).split(',')]

def get_trailer_url(film_url):
    """
    Generate potential trailer URL based on film URL
    """
    if pd.isna(film_url):
        return None
    # This is a placeholder - you might need to scrape or have actual trailer links
    return f"{film_url}#trailer"

def search_youtube_trailer(film_title, director=None, year=None):
    """
    Search for film trailer on YouTube and return the URL
    """
    try:
        # Construct search query
        search_query = f"{film_title} trailer"
        if year:
            search_query += f" {year}"
        if director:
            search_query += f" {director}"
        
        # Create YouTube search URL
        encoded_query = quote_plus(search_query)
        youtube_search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        # For now, return the search URL. In a production app, you could:
        # 1. Use YouTube Data API to get actual video URLs
        # 2. Use youtube-search-python library
        # 3. Web scrape the results page
        
        return youtube_search_url
        
    except Exception as e:
        st.error(f"Error searching for trailer: {str(e)}")
        return None

def save_shortlist_to_file(shortlist, filename="miff_shortlist.json"):
    """
    Save shortlist to a JSON file
    """
    try:
        shortlist_data = {
            "films": list(shortlist),
            "saved_at": pd.Timestamp.now().isoformat()
        }
        with open(filename, 'w') as f:
            json.dump(shortlist_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving shortlist: {str(e)}")
        return False

def load_shortlist_from_file(filename="miff_shortlist.json"):
    """
    Load shortlist from a JSON file
    """
    try:
        with open(filename, 'r') as f:
            shortlist_data = json.load(f)
        return set(shortlist_data.get("films", []))
    except FileNotFoundError:
        return set()
    except Exception as e:
        st.error(f"Error loading shortlist: {str(e)}")
        return set()

def main():
    st.title("🎬 MIFF 2025 Film Browser")
    st.markdown("Browse, filter, and shortlist films from the Melbourne International Film Festival 2025")
    
    # Load data directly from local file
    processed_df = load_miff_data()
    
    if len(processed_df) == 0:
        st.warning("No data found. Please check if 'miff_2025_complete.csv' exists in the current directory.")
        return
    
    # Display column information for debugging
    st.sidebar.header("📊 Data Info")
    with st.sidebar.expander("Column Information"):
        st.write("Available columns:")
        for col in processed_df.columns:
            st.write(f"- {col}")
    
    with st.sidebar.expander("ℹ️ Trailer Search Info"):
        st.markdown("""
        **Trailer Search Features:**
        - 🎥 Search YouTube for film trailers
        - 🔍 Uses film title, director, and year
        - 💾 Trailer links persist in your session
        
        **Note:** For better results, consider adding:
        - YouTube Data API integration
        - `youtube-search-python` library
        """)
    
    # Get unique films (deduplicate by title)
    unique_films = processed_df.drop_duplicates(subset=['title']).copy()
    
    # Extract all unique genres and languages
    all_genres = set()
    all_languages = set()
    
    for _, row in unique_films.iterrows():
        if pd.notna(row.get('genres')):
            all_genres.update(parse_genres(row['genres']))
        if pd.notna(row.get('languages')):
            all_languages.update(parse_languages(row['languages']))
    
    all_genres = sorted(list(all_genres))
    all_languages = sorted(list(all_languages))
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Genre filter
    selected_genres = st.sidebar.multiselect(
        "Select Genres:",
        all_genres,
        help="Select one or more genres to filter films"
    )
    
    # Language filter  
    selected_languages = st.sidebar.multiselect(
        "Select Languages:",
        all_languages,
        help="Select one or more languages to filter films"
    )
    
    # Text search
    search_term = st.sidebar.text_input(
        "Search films:",
        placeholder="Search in title, director, or description..."
    )
    
    # Filter films
    filtered_films = unique_films.copy()
    
    if selected_genres:
        filtered_films = filtered_films[
            filtered_films['genres'].apply(
                lambda x: any(genre in parse_genres(x) for genre in selected_genres)
            )
        ]
    
    if selected_languages:
        filtered_films = filtered_films[
            filtered_films['languages'].apply(
                lambda x: any(lang in parse_languages(x) for lang in selected_languages)
            )
        ]
    
    if search_term:
        search_mask = (
            filtered_films['title'].str.contains(search_term, case=False, na=False) |
            filtered_films['director'].str.contains(search_term, case=False, na=False) |
            filtered_films['description'].str.contains(search_term, case=False, na=False)
        )
        filtered_films = filtered_films[search_mask]
    
    # Initialize shortlist in session state
    if 'shortlist' not in st.session_state:
        st.session_state.shortlist = set()
    
    # Shortlist management in sidebar
    st.sidebar.header("💾 Shortlist Management")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("💾 Save Shortlist"):
            if save_shortlist_to_file(st.session_state.shortlist):
                st.sidebar.success("✅ Shortlist saved!")
            else:
                st.sidebar.error("❌ Failed to save")
    
    with col2:
        if st.button("📂 Load Shortlist"):
            loaded_shortlist = load_shortlist_from_file()
            if loaded_shortlist:
                st.session_state.shortlist = loaded_shortlist
                st.sidebar.success(f"✅ Loaded {len(loaded_shortlist)} films!")
                st.rerun()
            else:
                st.sidebar.info("No saved shortlist found")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(f"🎭 Films ({len(filtered_films)} found)")
        
        if len(filtered_films) == 0:
            st.warning("No films match your current filters.")
        else:
            # Display films
            for idx, (_, film) in enumerate(filtered_films.iterrows()):
                with st.expander(f"🎬 {film['title']}", expanded=False):
                    film_col1, film_col2 = st.columns([3, 1])
                    
                    with film_col1:
                        st.markdown(f"**Director:** {film.get('director', 'N/A')}")
                        
                        if pd.notna(film.get('genres')):
                            genres_list = parse_genres(film['genres'])
                            if genres_list:
                                st.markdown(f"**Genres:** {', '.join(genres_list)}")
                        
                        if pd.notna(film.get('languages')):
                            languages_list = parse_languages(film['languages'])
                            if languages_list:
                                st.markdown(f"**Languages:** {', '.join(languages_list)}")
                        
                        if pd.notna(film.get('runtime')):
                            st.markdown(f"**Runtime:** {film['runtime']}")
                        
                        if pd.notna(film.get('year')):
                            st.markdown(f"**Year:** {film['year']}")
                        
                        if pd.notna(film.get('description')):
                            st.markdown(f"**Description:** {film['description']}")
                    
                    with film_col2:
                        # Shortlist button
                        film_title = film['title']
                        if film_title in st.session_state.shortlist:
                            if st.button(f"❤️ Remove from shortlist", key=f"remove_{idx}"):
                                st.session_state.shortlist.remove(film_title)
                                st.rerun()
                        else:
                            if st.button(f"🤍 Add to shortlist", key=f"add_{idx}"):
                                st.session_state.shortlist.add(film_title)
                                st.rerun()
                        
                        # Trailer link (if available)
                        if pd.notna(film.get('film_url')):
                            trailer_url = get_trailer_url(film['film_url'])
                            st.markdown(f"[🎥 Film Page]({film['film_url']})")
                        
                        # Sessions button
                        if st.button(f"📅 View Sessions", key=f"sessions_{idx}"):
                            st.session_state.selected_film_for_sessions = film_title
    
    with col2:
        st.header("❤️ Your Shortlist")
        
        if not st.session_state.shortlist:
            st.info("No films in your shortlist yet. Add some films to see them here!")
        else:
            st.markdown(f"**{len(st.session_state.shortlist)} films shortlisted**")
            
            # Display shortlisted films with trailer search
            for film_title in st.session_state.shortlist:
                with st.expander(f"🎬 {film_title}", expanded=False):
                    # Get film details for trailer search
                    film_details = unique_films[unique_films['title'] == film_title]
                    if not film_details.empty:
                        film_row = film_details.iloc[0]
                        director = film_row.get('director', '')
                        year = film_row.get('year', '')
                        
                        # Film info
                        if pd.notna(director):
                            st.markdown(f"**Director:** {director}")
                        if pd.notna(year):
                            st.markdown(f"**Year:** {year}")
                        
                        # Trailer search button
                        if st.button(f"🎥 Search Trailer on YouTube", key=f"trailer_{film_title}"):
                            trailer_url = search_youtube_trailer(film_title, director, year)
                            if trailer_url:
                                st.markdown(f"[🎬 Watch Trailer on YouTube]({trailer_url})")
                                # Store the trailer URL in session state for persistence
                                if 'trailer_urls' not in st.session_state:
                                    st.session_state.trailer_urls = {}
                                st.session_state.trailer_urls[film_title] = trailer_url
                        
                        # Show stored trailer URL if available
                        if hasattr(st.session_state, 'trailer_urls') and film_title in st.session_state.trailer_urls:
                            st.markdown(f"[🎬 Watch Trailer on YouTube]({st.session_state.trailer_urls[film_title]})")
                        
                        # Remove from shortlist button
                        if st.button(f"🗑️ Remove", key=f"remove_shortlist_{film_title}"):
                            st.session_state.shortlist.remove(film_title)
                            # Also remove trailer URL if stored
                            if hasattr(st.session_state, 'trailer_urls') and film_title in st.session_state.trailer_urls:
                                del st.session_state.trailer_urls[film_title]
                            st.rerun()
            
            st.markdown("---")
            
            # Export shortlist
            if st.button("📋 Export Shortlist as Text"):
                shortlist_text = "\n".join([f"- {title}" for title in st.session_state.shortlist])
                st.text_area("Copy your shortlist:", shortlist_text, height=200)
            
            # Clear shortlist
            if st.button("🗑️ Clear Shortlist"):
                st.session_state.shortlist.clear()
                if hasattr(st.session_state, 'trailer_urls'):
                    st.session_state.trailer_urls.clear()
                st.rerun()
    
    # Show sessions for selected film
    if hasattr(st.session_state, 'selected_film_for_sessions'):
        selected_film = st.session_state.selected_film_for_sessions
        st.header(f"📅 Sessions for: {selected_film}")
        
        # Get all sessions for this film
        film_sessions = processed_df[processed_df['title'] == selected_film].copy()
        
        if len(film_sessions) > 0:
            # Group by date
            film_sessions['session_date'] = pd.to_datetime(film_sessions['session_date'], errors='coerce')
            film_sessions = film_sessions.sort_values('session_date')
            
            for _, session in film_sessions.iterrows():
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if pd.notna(session['session_date']):
                        st.markdown(f"**📅 {session['session_date'].strftime('%B %d, %Y') if hasattr(session['session_date'], 'strftime') else session['session_date']}**")
                
                with col2:
                    if pd.notna(session['session_time']):
                        st.markdown(f"**🕐 {session['session_time']}**")
                
                with col3:
                    if pd.notna(session['session_venue']):
                        st.markdown(f"**📍 {session['session_venue']}**")
                
                if pd.notna(session.get('session_context')):
                    st.markdown(f"*{session['session_context']}*")
                
                st.markdown("---")
        else:
            st.warning("No session information found for this film.")
        
        if st.button("❌ Close Sessions"):
            del st.session_state.selected_film_for_sessions
            st.rerun()

if __name__ == "__main__":
    main()