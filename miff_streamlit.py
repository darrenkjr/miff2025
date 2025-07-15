import streamlit as st
from streamlit_calendar import calendar
import pandas as pd
import re
import json
import requests
from urllib.parse import quote_plus, urlencode, parse_qs
from typing import List, Dict
from datetime import datetime, timedelta
import pytz
import base64
import urllib.parse

# Page configuration
st.set_page_config(
    page_title="MIFF 2025 Film Browser",
    page_icon="🎬",
    layout="wide"
)

# Function to encode shortlist for URL sharing
def encode_shortlist_for_url(shortlist):
    """
    Encode shortlist for URL sharing using base64
    """
    try:
        shortlist_data = {
            "films": list(shortlist),
            "shared_at": datetime.now().isoformat()
        }
        json_str = json.dumps(shortlist_data)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
        return encoded
    except Exception as e:
        st.error(f"Error encoding shortlist: {str(e)}")
        return None

def decode_shortlist_from_url(encoded_data):
    """
    Decode shortlist from URL parameter
    """
    try:
        decoded = base64.urlsafe_b64decode(encoded_data.encode()).decode()
        shortlist_data = json.loads(decoded)
        return set(shortlist_data.get("films", []))
    except Exception as e:
        st.error(f"Error decoding shared shortlist: {str(e)}")
        return set()

def generate_share_url(shortlist):
    """
    Generate a shareable URL with the shortlist encoded
    """
    encoded_shortlist = encode_shortlist_for_url(shortlist)
    if encoded_shortlist:
        # Check if running locally or on deployment
        try:
            # For deployed app
            base_url = "https://miff2025browser.streamlit.app"
            # For local development, you can uncomment the line below:
            # base_url = "http://localhost:8501"
        except:
            base_url = "https://miff2025browser.streamlit.app"
        
        share_url = f"{base_url}?shortlist={encoded_shortlist}"
        return share_url
    return None

def check_for_shared_shortlist():
    """
    Check URL parameters for shared shortlist and load it
    """
    # Use the latest Streamlit query params API
    query_params = st.query_params
    
    # Get the shortlist parameter
    shortlist_param = query_params.get("shortlist")
    
    if shortlist_param:
        shared_shortlist = decode_shortlist_from_url(shortlist_param)
        
        if shared_shortlist:
            # Show import dialog
            st.sidebar.success(f"🔗 Shared shortlist detected! ({len(shared_shortlist)} films)")
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("📥 Import", key="import_shared"):
                    st.session_state.shortlist = shared_shortlist
                    st.session_state.imported_shared = True
                    # Clear the URL parameter after importing
                    st.query_params.clear()
                    st.success(f"✅ Imported {len(shared_shortlist)} films!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Ignore", key="ignore_shared"):
                    st.session_state.ignored_shared = True
                    # Clear the URL parameter
                    st.query_params.clear()
                    st.rerun()
            
            # Show what would be imported
            with st.sidebar.expander("🔍 Preview Shared Films"):
                for film in sorted(shared_shortlist):
                    st.write(f"• {film}")

# Function to load and process the data
@st.cache_data
def load_miff_data():
    """
    Load and process MIFF data from local file
    """
    try:
        # Load the main data file
        df = pd.read_csv('miff_2025_complete_summary.csv')
        
        # Display basic info about the loaded data
        st.sidebar.info(f"✅ Loaded {len(df)} records from miff_2025_complete_summary.csv")
        
        return df
        
    except FileNotFoundError:
        st.error("❌ Could not find 'miff_2025_complete_summary.csv' in the current directory.")
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

def parse_strands(strand_string):
    """Parse strand string into list"""
    if pd.isna(strand_string) or strand_string == '':
        return []
    return [s.strip() for s in str(strand_string).split(',')]

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

def parse_session_datetime(session_date, session_time):
    """Parse session date and time into datetime object"""
    try:
        # Handle different date formats
        if pd.isna(session_date) or pd.isna(session_time):
            return None
        
        # Convert session_date to string if it's not already
        date_str = str(session_date).strip()
        time_str = str(session_time).strip()
        
        # Parse date - handle formats like "25 Aug" (assume 2025)
        if re.match(r'\d{1,2}\s+\w+', date_str):
            # Format like "25 Aug" - add 2025
            date_str = f"{date_str} 2025"
            dt = datetime.strptime(date_str, '%d %b %Y')
        elif re.match(r'\d{1,2}\s+\w+\s+\d{4}', date_str):
            # Format like "25 Aug 2025"
            dt = datetime.strptime(date_str, '%d %b %Y')
        else:
            # Try to parse as is with pandas
            dt = pd.to_datetime(date_str, errors='coerce')
            if pd.isna(dt):
                return None
            dt = dt.to_pydatetime()
        
        # Parse time - handle various formats
        time_str = time_str.replace('.', ':')  # Handle 6.15pm format
        time_str = time_str.replace(' ', '')   # Remove spaces
        
        if 'pm' in time_str.lower():
            time_obj = datetime.strptime(time_str.lower(), '%I:%M%p').time()
        elif 'am' in time_str.lower():
            time_obj = datetime.strptime(time_str.lower(), '%I:%M%p').time()
        elif ':' in time_str:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
        else:
            # Handle cases like "6pm" or "10am"
            if 'pm' in time_str.lower():
                hour = int(time_str.lower().replace('pm', ''))
                if hour != 12:
                    hour += 12
                time_obj = datetime.strptime(f"{hour}:00", '%H:%M').time()
            elif 'am' in time_str.lower():
                hour = int(time_str.lower().replace('am', ''))
                if hour == 12:
                    hour = 0
                time_obj = datetime.strptime(f"{hour}:00", '%H:%M').time()
            else:
                return None
        
        # Combine date and time
        combined = datetime.combine(dt.date(), time_obj)
        
        # Set to Melbourne timezone
        melbourne_tz = pytz.timezone('Australia/Melbourne')
        return melbourne_tz.localize(combined)
        
    except Exception as e:
        print(f"Error parsing datetime: {session_date} {session_time} - {e}")
        return None

def create_calendar_events(shortlist_sessions):
    """Create calendar events from shortlist sessions"""
    events = []
    
    for _, session in shortlist_sessions.iterrows():
        dt = parse_session_datetime(session['session_date'], session['session_time'])
        if dt:
            # Assume 2 hour duration for films
            end_dt = dt + timedelta(hours=2)
            
            event = {
                'title': session['title'],
                'start': dt.isoformat(),
                'end': end_dt.isoformat(),
                'resourceId': session.get('session_venue', 'Unknown'),
                'extendedProps': {
                    'director': session.get('director', ''),
                    'venue': session.get('session_venue', ''),
                    'runtime': session.get('runtime', ''),
                    'description': session.get('description', '')[:100] + '...' if session.get('description') else ''
                }
            }
            events.append(event)
    
    return events

def generate_ics_file(shortlist_sessions):
    """Generate ICS file content from shortlist sessions"""
    ics_content = ["BEGIN:VCALENDAR"]
    ics_content.append("VERSION:2.0")
    ics_content.append("PRODID:-//MIFF 2025 Shortlist//EN")
    ics_content.append("CALSCALE:GREGORIAN")
    ics_content.append("METHOD:PUBLISH")
    
    for _, session in shortlist_sessions.iterrows():
        dt = parse_session_datetime(session['session_date'], session['session_time'])
        if dt:
            # Convert to UTC for ICS
            utc_dt = dt.astimezone(pytz.UTC)
            end_dt = utc_dt + timedelta(hours=2)  # Assume 2 hour duration
            
            # Format datetime for ICS (YYYYMMDDTHHMMSSZ)
            start_str = utc_dt.strftime('%Y%m%dT%H%M%SZ')
            end_str = end_dt.strftime('%Y%m%dT%H%M%SZ')
            
            # Create unique ID
            uid = f"miff2025-{session.get('film_id', 'unknown')}-{start_str}"
            
            ics_content.append("BEGIN:VEVENT")
            ics_content.append(f"UID:{uid}")
            ics_content.append(f"DTSTART:{start_str}")
            ics_content.append(f"DTEND:{end_str}")
            ics_content.append(f"SUMMARY:{session['title']}")
            
            # Add description
            description_parts = []
            description_parts.append(f"Film: {session['title']}")
            description_parts.append(f"Venue: {session['session_venue']}")
            description_parts.append(f"Director: {session['director']}")
            description_parts.append(f"Runtime: {session['runtime']}")
            description_parts.append(f"Description: {session['description']}")
            description_parts.append(f"Film URL: {session['film_url']}")
            
            if description_parts:
                ics_content.append(f"DESCRIPTION:{'\\n'.join(description_parts)}")

            
            # Add location
            if session.get('session_venue'):
                ics_content.append(f"LOCATION:{session['session_venue']}")
            
            # Add URL if available
            if session.get('film_url'):
                ics_content.append(f"URL:{session['film_url']}")
            
            ics_content.append("END:VEVENT")
    
    ics_content.append("END:VCALENDAR")
    return "\n".join(ics_content)

def main():
    st.title("🎬 MIFF 2025 Film Browser")
    st.markdown("Browse, filter, and shortlist films from the Melbourne International Film Festival 2025")
    st.markdown("This is a personal project and not affiliated with the Melbourne International Film Festival. I make no guarantees about the accuracy of the data, but if this is helpful to you, feel free to share this with your friends!")
    st.markdown("Please report any issues or suggestions in the github repo: https://github.com/darrenkjr/miff2025/issues/new ")
    
    # Initialize session state variables if they don't exist
    if 'shortlist' not in st.session_state:
        st.session_state.shortlist = set()
    if 'imported_shared' not in st.session_state:
        st.session_state.imported_shared = False
    if 'ignored_shared' not in st.session_state:
        st.session_state.ignored_shared = False
    
    # Check for shared shortlist in URL parameters (only if not already imported/ignored)
    if not st.session_state.imported_shared and not st.session_state.ignored_shared:
        check_for_shared_shortlist()
    
    # Load data directly from local file
    processed_df = load_miff_data()
    
    if processed_df.empty:
        st.error("No data loaded. Please check your CSV file.")
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

    all_genres = set()
    all_languages = set()
    all_strands = set()
    
    for _, row in unique_films.iterrows():
        if pd.notna(row.get('genres')):
            all_genres.update(parse_genres(row['genres']))
        if pd.notna(row.get('languages')):
            all_languages.update(parse_languages(row['languages']))
        if pd.notna(row.get('strands')):
            all_strands.update(parse_strands(row['strands']))
    
    all_genres = sorted(list(all_genres))
    all_languages = sorted(list(all_languages))
    all_strands = sorted(list(all_strands))
    
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

    selected_strands = st.sidebar.multiselect(
        "Select Strands:",
        all_strands,
        help="Select one or more strands to filter films"
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
    
    if selected_strands:
        filtered_films = filtered_films[
            filtered_films['strands'].apply(
                lambda x: any(strand in parse_strands(x) for strand in selected_strands)
            )
        ]
    if search_term:
        search_mask = (
            filtered_films['title'].str.contains(search_term, case=False, na=False) |
            filtered_films['director'].str.contains(search_term, case=False, na=False) |
            filtered_films['description'].str.contains(search_term, case=False, na=False)
        )
        filtered_films = filtered_films[search_mask]
    
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
    
    # Main content area - only show if not in dashboard mode
    if not (hasattr(st.session_state, 'show_shortlist_detail') and st.session_state.show_shortlist_detail):
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

                            if pd.notna(film.get('strands')):
                                strands_list = parse_strands(film['strands'])
                                if strands_list:
                                    st.markdown(f"**Strands:** {', '.join(strands_list)}")
                            
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
                st.info("No films in your shortlist yet. Add some films to see them here or import a shortlist from a friend!")
                
                # File uploader for JSON import
                uploaded_file = st.file_uploader("Import Shortlist from JSON", type="json")
                if uploaded_file is not None:
                    try:
                        shortlist_data = json.load(uploaded_file)
                        imported_films = set(shortlist_data.get("films", []))
                        if imported_films:
                            st.session_state.shortlist = imported_films
                            st.success(f"✅ Imported {len(imported_films)} films!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error importing shortlist: {str(e)}")
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
                
                # Share shortlist section
                st.subheader("🔗 Share Your Shortlist")
                
                # Generate share URL
                if st.button("🔗 Generate Share Link", help="Create a link to share your shortlist with friends"):
                    share_url = generate_share_url(st.session_state.shortlist)
                    if share_url:
                        st.success("✅ Share link generated!")
                        st.code(share_url, language="text")
                        st.markdown("**Copy this link and send it to your friends!**")
                        st.info("💡 Tip: Anyone with this link can import your shortlist into their own browser")
                        # Store the generated URL for display
                        st.session_state.current_share_url = share_url
                    else:
                        st.error("❌ Failed to generate share link")
                
                
                st.markdown("---")
                
                # Load shortlist detail button
                if st.button("📋 Load Shortlist Detail"):
                    st.session_state.show_shortlist_detail = True
                    st.rerun()
                
                # Clear shortlist
                if st.button("🗑️ Clear Shortlist"):
                    st.session_state.shortlist.clear()
                    if hasattr(st.session_state, 'trailer_urls'):
                        st.session_state.trailer_urls.clear()
                    if hasattr(st.session_state, 'current_share_url'):
                        del st.session_state.current_share_url
                    st.rerun()

        
        # Show sessions for selected film (only in browse mode)
        if hasattr(st.session_state, 'selected_film_for_sessions'):
            selected_film = st.session_state.selected_film_for_sessions
            st.header(f"📅 Sessions for: {selected_film}")
            
            # Get all sessions for this film
            film_sessions = processed_df[processed_df['title'] == selected_film].copy()
            
            if len(film_sessions) > 0:
                # Process and sort sessions with proper date handling
                film_sessions['session_date_parsed'] = film_sessions.apply(
                    lambda row: parse_session_datetime(row['session_date'], '12:00pm'), axis=1
                )
                film_sessions = film_sessions.sort_values('session_date_parsed')
                
                # Group sessions by date for better display
                session_dates = []
                for _, row in film_sessions.iterrows():
                    if row['session_date_parsed']:
                        session_dates.append(row['session_date_parsed'].date())
                
                unique_dates = sorted(list(set(session_dates)))
                
                if len(unique_dates) > 0:
                    for date in unique_dates:
                        date_sessions = film_sessions[
                            film_sessions['session_date_parsed'].dt.date == date
                        ]
                        
                        st.markdown(f"**📅 {date.strftime('%A, %B %d, %Y')}**")
                        
                        for _, session in date_sessions.iterrows():
                            session_col1, session_col2, session_col3 = st.columns([1, 2, 1])
                            
                            with session_col1:
                                if pd.notna(session['session_time']):
                                    st.markdown(f"🕐 **{session['session_time']}**")
                            
                            with session_col2:
                                if pd.notna(session['session_venue']):
                                    st.markdown(f"📍 {session['session_venue']}")
                            
                            with session_col3:
                                pass
                            
                            if pd.notna(session.get('session_context')):
                                st.markdown(f"*{session['session_context']}*")
                        
                        st.markdown("")
                else:
                    # Fallback to simple format
                    for _, session in film_sessions.iterrows():
                        session_info = []
                        if pd.notna(session.get('session_date')):
                            session_info.append(f"📅 {session['session_date']}")
                        if pd.notna(session.get('session_time')):
                            session_info.append(f"🕐 {session['session_time']}")
                        if pd.notna(session.get('session_venue')):
                            session_info.append(f"📍 {session['session_venue']}")
                        
                        if session_info:
                            st.markdown(" | ".join(session_info))
                        
                        if pd.notna(session.get('session_context')):
                            st.markdown(f"*{session['session_context']}*")
            else:
                st.warning("No session information found for this film.")
            
            if st.button("❌ Close Sessions"):
                del st.session_state.selected_film_for_sessions
                st.rerun()
    
    # Shortlist Dashboard View (keeping the rest of the original dashboard code...)
    if hasattr(st.session_state, 'show_shortlist_detail') and st.session_state.show_shortlist_detail:
        # Dashboard header with navigation
        dashboard_col1, dashboard_col2 = st.columns([3, 1])
        
        with dashboard_col1:
            st.title("📋 Shortlist Dashboard")
            st.markdown("**Your complete festival planning view**")
        
        with dashboard_col2:
            if st.button("⬅️ Back to Browse"):
                st.session_state.show_shortlist_detail = False
                st.rerun()
        
        if not st.session_state.shortlist:
            st.info("Your shortlist is empty. Go back to browse and add some films!")
            return
        
        st.markdown(f"**📊 {len(st.session_state.shortlist)} films in your shortlist**")
        st.markdown("---")
        
        for idx, film_title in enumerate(sorted(st.session_state.shortlist)):
            # Get film details
            film_details = unique_films[unique_films['title'] == film_title]
            if film_details.empty:
                continue
            
            film_row = film_details.iloc[0]
            
            # Create film section
            st.subheader(f"🎬 {film_title}")
            
            # Film information in columns
            info_col1, info_col2, info_col3 = st.columns([2, 1, 1])
            
            with info_col1:
                if pd.notna(film_row.get('director')):
                    st.markdown(f"**Director:** {film_row['director']}")
                if pd.notna(film_row.get('genres')):
                    genres_list = parse_genres(film_row['genres'])
                    if genres_list:
                        st.markdown(f"**Genres:** {', '.join(genres_list)}")
                if pd.notna(film_row.get('runtime')):
                    st.markdown(f"**Runtime:** {film_row['runtime']}")
                if pd.notna(film_row.get('year')):
                    st.markdown(f"**Year:** {film_row['year']}")
                if pd.notna(film_row.get('strands')):
                    strands_list = parse_strands(film_row['strands'])
                    if strands_list:
                        st.markdown(f"**Strands:** {', '.join(strands_list)}")
                if pd.notna(film_row.get('languages')):
                    languages_list = parse_languages(film_row['languages'])
                    if languages_list:
                        st.markdown(f"**Languages:** {', '.join(languages_list)}")
                if pd.notna(film_row.get('description')):
                    st.markdown(f"**Description:** {film_row['description']}")
            
            with info_col2:
                # Trailer search
                if st.button(f"🎥 Search Trailer", key=f"detail_trailer_{idx}"):
                    director = film_row.get('director', '')
                    year = film_row.get('year', '')
                    trailer_url = search_youtube_trailer(film_title, director, year)
                    if trailer_url:
                        if 'trailer_urls' not in st.session_state:
                            st.session_state.trailer_urls = {}
                        st.session_state.trailer_urls[film_title] = trailer_url
                        st.rerun()
                
                # Show trailer link if available
                if hasattr(st.session_state, 'trailer_urls') and film_title in st.session_state.trailer_urls:
                    st.markdown(f"[🎬 Watch Trailer]({st.session_state.trailer_urls[film_title]})")
            
            with info_col3:
                # Film page link
                if pd.notna(film_row.get('film_url')):
                    st.markdown(f"[🎭 Film Page]({film_row['film_url']})")
                
                # Remove from shortlist
                if st.button(f"🗑️ Remove", key=f"dashboard_remove_{idx}"):
                    st.session_state.shortlist.remove(film_title)
                    if hasattr(st.session_state, 'trailer_urls') and film_title in st.session_state.trailer_urls:
                        del st.session_state.trailer_urls[film_title]
                    st.rerun()
            

            if pd.notna(film_row.get('synopsis')):
                with st.expander(f"📝 Synopsis"):
                    st.markdown(film_row['synopsis'])
            
            # Sessions for this film
            film_sessions = processed_df[processed_df['title'] == film_title].copy()
            if len(film_sessions) > 0:
                st.markdown("**🗓️ Available Sessions:**")
                
                # Process and sort sessions with proper date handling
                film_sessions['session_date_parsed'] = film_sessions.apply(
                    lambda row: parse_session_datetime(row['session_date'], '12:00pm'), axis=1
                )
                film_sessions = film_sessions.sort_values('session_date_parsed')
                
                # Group sessions by date for better display
                session_dates = []
                for _, row in film_sessions.iterrows():
                    if row['session_date_parsed']:
                        session_dates.append(row['session_date_parsed'].date())
                
                unique_dates = sorted(list(set(session_dates)))
                
                if len(unique_dates) > 0:
                    for date in unique_dates:
                        date_sessions = film_sessions[
                            film_sessions['session_date_parsed'].dt.date == date
                        ]
                        
                        st.markdown(f"**📅 {date.strftime('%A, %B %d, %Y')}**")
                        
                        for _, session in date_sessions.iterrows():
                            session_col1, session_col2, session_col3 = st.columns([1, 2, 1])
                            
                            with session_col1:
                                if pd.notna(session['session_time']):
                                    st.markdown(f"🕐 **{session['session_time']}**")
                            
                            with session_col2:
                                if pd.notna(session['session_venue']):
                                    st.markdown(f"📍 {session['session_venue']}")
                            
                            with session_col3:
                                # You could add a "Book" button here if you have booking URLs
                                pass
                            
                            if pd.notna(session.get('session_context')):
                                st.markdown(f"*{session['session_context']}*")
                        
                        st.markdown("")  # Add spacing between dates
                else:
                    # If no proper dates, show all sessions in simple format
                    for _, session in film_sessions.iterrows():
                        session_info = []
                        if pd.notna(session.get('session_date')):
                            session_info.append(f"📅 {session['session_date']}")
                        if pd.notna(session.get('session_time')):
                            session_info.append(f"🕐 {session['session_time']}")
                        if pd.notna(session.get('session_venue')):
                            session_info.append(f"📍 {session['session_venue']}")
                        
                        if session_info:
                            st.markdown(" | ".join(session_info))
                        
                        if pd.notna(session.get('session_context')):
                            st.markdown(f"*{session['session_context']}*")
            else:
                st.warning("⚠️ No session information available for this film")
            
            # Add separator between films
            st.markdown("---")
        
        # Calendar View Section
        st.header("📅 Calendar View")
        
        # Get all sessions for shortlisted films
        shortlist_sessions = processed_df[processed_df['title'].isin(st.session_state.shortlist)].copy()
        sessions_with_times = shortlist_sessions[shortlist_sessions['session_time'].notna() & 
                                               shortlist_sessions['session_date'].notna()]
        
        if len(sessions_with_times) > 0:
            # Create calendar events
            events = create_calendar_events(sessions_with_times)
            
            if events:
                # Calendar configuration - start from MIFF opening day
                calendar_options = {
                    "editable": False,
                    "navLinks": True,
                    "dayMaxEvents": 3,
                    "headerToolbar": {
                        "left": "prev,next today",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek,timeGridDay"
                    },
                    "initialView": "timeGridWeek",
                    "initialDate": "2025-08-07",  # MIFF opening day
                    "height": 600,
                    "slotMinTime": "09:00:00",
                    "slotMaxTime": "23:00:00",
                    "validRange": {
                        "start": "2025-08-01",
                        "end": "2025-08-31"
                    }
                }
                
                # Display calendar
                calendar_component = calendar(
                    events=events,
                    options=calendar_options,
                    key="miff_calendar"
                )
                
                # Show event details if clicked
                if calendar_component.get("eventClick"):
                    event_details = calendar_component["eventClick"]["event"]
                    st.info(f"**{event_details['title']}**\n"
                           f"📍 {event_details.get('extendedProps', {}).get('venue', 'Unknown venue')}\n"
                           f"🎬 Director: {event_details.get('extendedProps', {}).get('director', 'Unknown')}\n"
                           f"⏱️ {event_details.get('extendedProps', {}).get('runtime', 'Unknown runtime')}")
            else:
                st.warning("Unable to parse session times for calendar display.")
            
            # Export buttons
            st.markdown("### 📤 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # ICS Export
                ics_content = generate_ics_file(sessions_with_times)
                st.download_button(
                    label="📅 Download Calendar (ICS)",
                    data=ics_content,
                    file_name=f"miff_2025_shortlist_{datetime.now().strftime('%Y%m%d')}.ics",
                    mime="text/calendar",
                    help="Download as calendar file to import into Google Calendar, Outlook, etc."
                )
            
            with col2:
                # CSV Export of sessions
                csv_data = sessions_with_times[['title', 'director', 'session_date', 'session_time', 
                                               'session_venue', 'runtime', 'film_url']].to_csv(index=False)
                st.download_button(
                    label="📊 Download Sessions (CSV)",
                    data=csv_data,
                    file_name=f"miff_2025_sessions_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    help="Download session details as spreadsheet"
                )
            
            # Statistics
            st.markdown("### 📊 Schedule Summary")
            
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            
            with stats_col1:
                total_sessions = len(sessions_with_times)
                st.metric("Total Sessions", total_sessions)
            
            with stats_col2:
                unique_venues = sessions_with_times['session_venue'].nunique()
                st.metric("Unique Venues", unique_venues)
            
            with stats_col3:
                date_range = sessions_with_times['session_date'].nunique()
                st.metric("Festival Days", date_range)
            
            # Venue breakdown
            venue_counts = sessions_with_times['session_venue'].value_counts()
            if len(venue_counts) > 0:
                st.markdown("**Sessions by Venue:**")
                for venue, count in venue_counts.items():
                    st.write(f"📍 {venue}: {count} sessions")
        
        else:
            st.info("No sessions with valid dates/times found in your shortlist.")
            
            # Still offer shortlist export
            if st.button("📋 Export Shortlist (JSON)"):
                shortlist_data = {
                    "films": list(st.session_state.shortlist),
                    "exported_at": datetime.now().isoformat()
                }
                st.download_button(
                    label="Download Shortlist",
                    data=json.dumps(shortlist_data, indent=2),
                    file_name=f"miff_shortlist_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()