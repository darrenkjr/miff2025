import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
import json

class CompleteMIFFScraper:
    """
    Complete MIFF scraper that combines:
    1. Film details from individual film pages
    2. Session times and venues from schedule grids
    3. Merges them into a comprehensive dataset
    """
    
    def __init__(self):
        self.base_url = "https://miff.com.au"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # MIFF 2025: August 7-24, 2025
        self.festival_start = datetime(2025, 8, 7)
        self.festival_end = datetime(2025, 8, 24)
        
        self.films_data = []
        self.sessions_data = []
        self.combined_data = []
    
    def get_all_film_urls(self):
        """Get all film URLs from the program pages"""
        print("Step 1: Discovering all films...")
        
        all_film_urls = set()
        
        for page in range(1, 25):  # Check up to 25 pages
            page_url = f"{self.base_url}/program/films?page={page}"
            print(f"  Checking page {page}...")
            
            try:
                response = self.session.get(page_url)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                page_films = 0
                for link in links:
                    href = link['href']
                    if '/program/film/' in href:
                        clean_href = href.split('#')[0]
                        full_url = urljoin(self.base_url, clean_href)
                        if full_url not in all_film_urls:
                            all_film_urls.add(full_url)
                            page_films += 1
                
                if page_films == 0:
                    break
                
                print(f"    Found {page_films} films")
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    Error on page {page}: {e}")
                break
        
        film_urls = list(all_film_urls)
        print(f"  Total films discovered: {len(film_urls)}")
        return film_urls
    
    def scrape_film_details(self, film_url):
        """Scrape detailed information from a film page"""
        try:
            response = self.session.get(film_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            film_data = {
                'film_url': film_url,
                'film_id': film_url.split('/')[-1],  # Extract ID from URL
                'title': '',
                'director': '',
                'year': '',
                'runtime': '',
                'countries': '',
                'languages': '',
                'genres': '',
                'premiere_status': '',
                'strands': '',
                'description': '',
                'synopsis': '',
                'viewer_advice': '',
                'review_quotes': ''
            }
            
            # Extract title
            title_elem = soup.find('h1') or soup.select_one('.title, .film-title')
            if title_elem:
                film_data['title'] = title_elem.get_text(strip=True)
            
            # Extract metadata from search links (this is very reliable)
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                
                if '/program/search?director=' in href:
                    film_data['director'] = text
                elif '/program/search?origin=' in href:
                    film_data['countries'] = film_data['countries'] + f", {text}" if film_data['countries'] else text
                elif '/program/search?language=' in href:
                    film_data['languages'] = film_data['languages'] + f", {text}" if film_data['languages'] else text
                elif '/program/search?genre=' in href:
                    film_data['genres'] = film_data['genres'] + f", {text}" if film_data['genres'] else text
                elif '/program/search?premiere-status=' in href:
                    film_data['premiere_status'] = text
                elif '/program/strand/' in href:
                    film_data['strands'] = film_data['strands'] + f", {text}" if film_data['strands'] else text
            
            # Extract year and runtime from text patterns
            page_text = soup.get_text()
            
            year_match = re.search(r'/\s*(\d{4})\s*/', page_text)
            if year_match:
                film_data['year'] = year_match.group(1)
            
            runtime_match = re.search(r'/\s*(\d+\s*mins?)\s*/', page_text)
            if runtime_match:
                film_data['runtime'] = runtime_match.group(1)
            
            # Extract viewer advice
            advice_match = re.search(r'Viewer Advice:\s*([^\n\r]+)', page_text)
            if advice_match:
                film_data['viewer_advice'] = advice_match.group(1).strip()
            
            # Extract descriptions from paragraphs
            paragraphs = soup.find_all('p')
            descriptions = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if (len(text) > 50 and 
                    not any(skip in text.lower() for skip in 
                           ['viewer advice', 'presented by', 'tickets', 'accessibility'])):
                    descriptions.append(text)
            
            if descriptions:
                film_data['description'] = descriptions[0]
                film_data['synopsis'] = ' '.join(descriptions)
            
            # Extract review quotes
            quotes = []
            for elem in soup.find_all(['blockquote', 'q']):
                quote = elem.get_text(strip=True)
                if quote and len(quote) > 20:
                    quotes.append(quote)
            
            # Look for quoted text in paragraphs
            for p in paragraphs:
                text = p.get_text(strip=True)
                if '"' in text and ('–' in text or '—' in text) and len(text) > 30:
                    quotes.append(text)
            
            film_data['review_quotes'] = ' | '.join(quotes[:3])  # Limit to 3 quotes
            
            return film_data
            
        except Exception as e:
            print(f"    Error scraping {film_url}: {e}")
            return None
    
    def scrape_all_films(self):
        """Scrape all film details"""
        print("Step 2: Scraping film details...")
        
        film_urls = self.get_all_film_urls()
        
        for i, film_url in enumerate(film_urls, 1):
            print(f"  Scraping {i}/{len(film_urls)}: {film_url.split('/')[-1]}")
            
            film_data = self.scrape_film_details(film_url)
            if film_data:
                self.films_data.append(film_data)
                print(f"    ✓ {film_data['title']}")
            
            time.sleep(1)  # Be respectful
        
        print(f"Step 2 complete: {len(self.films_data)} films scraped")
        return self.films_data
    
    def generate_festival_dates(self):
        """Generate all festival dates"""
        dates = []
        current_date = self.festival_start
        while current_date <= self.festival_end:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        return dates
    
    def scrape_schedule_for_date(self, date_str):
        """Scrape schedule for a specific date using the discovered URL pattern"""
        sessions = []
        
        # Try the main metropolitan venues
        url = f"{self.base_url}/program/schedule?day={date_str}&cstyle=0&venueloc=1"
        print(f"    Scraping {url}")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Method 1: Look for structured table/grid data
            
            # Find all links to films
            film_links = soup.find_all('a', href=True)
            for link in film_links:
                if '/program/film/' in link['href']:
                    
                    # Get film info
                    film_title = link.get_text(strip=True)
                    film_url = urljoin(self.base_url, link['href'].split('#')[0])
                    film_id = film_url.split('/')[-1]
                    
                    # Try to find context (venue, time) by looking at parent elements
                    context_text = ""
                    parent = link.parent
                    levels = 0
                    
                    while parent and levels < 4:  # Don't go too far up
                        parent_text = parent.get_text(strip=True)
                        context_text = parent_text + " " + context_text
                        parent = parent.parent
                        levels += 1
                    
                    # Extract time and venue from context
                    time_matches = re.findall(r'\d{1,2}:\d{2}\s*[ap]m|\d{1,2}\s*[ap]m', context_text)
                    venue_matches = re.findall(r'(ACMI|Hoyts[^|,\n]*|Capitol[^|,\n]*|Forum[^|,\n]*|Arts Centre[^|,\n]*)', context_text, re.I)
                    
                    session_data = {
                        'date': date_str,
                        'film_title': film_title,
                        'film_id': film_id,
                        'film_url': film_url,
                        'venue': venue_matches[0].strip() if venue_matches else 'Unknown',
                        'time': time_matches[0] if time_matches else 'Unknown',
                        'context': context_text[:200]  # First 200 chars of context
                    }
                    
                    sessions.append(session_data)
            
            # Method 2: Look for time slots in the page structure
            
            # The schedule appears to have time headers (9am, 10am, etc.)
            time_elements = soup.find_all(text=re.compile(r'\d{1,2}[ap]m'))
            for time_text in time_elements:
                time_clean = time_text.strip()
                if re.match(r'\d{1,2}[ap]m$', time_clean):  # Exact time match
                    
                    # Find the parent element and look for films in the same column/row
                    time_parent = time_text.parent if hasattr(time_text, 'parent') else None
                    if time_parent:
                        # Look for film links near this time
                        nearby_links = time_parent.find_all('a', href=True)
                        for link in nearby_links:
                            if '/program/film/' in link['href']:
                                
                                film_title = link.get_text(strip=True)
                                film_url = urljoin(self.base_url, link['href'].split('#')[0])
                                film_id = film_url.split('/')[-1]
                                
                                # Try to find venue info
                                container_text = time_parent.get_text(strip=True)
                                venue_matches = re.findall(r'(ACMI|Hoyts[^|,\n]*|Capitol[^|,\n]*|Forum[^|,\n]*)', container_text, re.I)
                                
                                session_data = {
                                    'date': date_str,
                                    'film_title': film_title,
                                    'film_id': film_id,
                                    'film_url': film_url,
                                    'venue': venue_matches[0].strip() if venue_matches else 'Unknown',
                                    'time': time_clean,
                                    'extraction_method': 'time_slot'
                                }
                                
                                sessions.append(session_data)
        
        except Exception as e:
            print(f"      Error scraping schedule for {date_str}: {e}")
        
        return sessions
    
    def scrape_all_sessions(self):
        """Scrape session data for all festival dates"""
        print("Step 3: Scraping session schedules...")
        
        festival_dates = self.generate_festival_dates()
        all_sessions = []
        
        for i, date_str in enumerate(festival_dates, 1):
            print(f"  Date {i}/{len(festival_dates)}: {date_str}")
            sessions = self.scrape_schedule_for_date(date_str)
            all_sessions.extend(sessions)
            print(f"    Found {len(sessions)} sessions")
            
            time.sleep(2)  # Be respectful
        
        # Deduplicate sessions
        unique_sessions = []
        seen = set()
        
        for session in all_sessions:
            key = (session['date'], session['film_id'], session['venue'], session['time'])
            if key not in seen:
                seen.add(key)
                unique_sessions.append(session)
        
        self.sessions_data = unique_sessions
        print(f"Step 3 complete: {len(unique_sessions)} unique sessions found")
        return unique_sessions
    
    def combine_films_and_sessions(self):
        """Combine film details with session information"""
        print("Step 4: Combining film details with session data...")
        
        # Create lookup dictionaries
        films_by_id = {film['film_id']: film for film in self.films_data}
        films_by_title = {film['title'].lower(): film for film in self.films_data if film['title']}
        
        # Group sessions by film
        sessions_by_film_id = {}
        sessions_by_film_title = {}
        
        for session in self.sessions_data:
            film_id = session['film_id']
            film_title = session['film_title'].lower()
            
            if film_id not in sessions_by_film_id:
                sessions_by_film_id[film_id] = []
            sessions_by_film_id[film_id].append(session)
            
            if film_title not in sessions_by_film_title:
                sessions_by_film_title[film_title] = []
            sessions_by_film_title[film_title].append(session)
        
        # Combine data
        combined = []
        
        for film in self.films_data:
            film_id = film['film_id']
            film_title = film['title'].lower()
            
            # Find sessions for this film
            film_sessions = sessions_by_film_id.get(film_id, [])
            
            # If no sessions found by ID, try by title
            if not film_sessions and film_title:
                film_sessions = sessions_by_film_title.get(film_title, [])
            
            if film_sessions:
                # Create one row per session
                for session in film_sessions:
                    combined_row = film.copy()  # Start with film data
                    combined_row.update({
                        'session_date': session['date'],
                        'session_venue': session['venue'],
                        'session_time': session['time'],
                        'session_context': session.get('context', ''),
                    })
                    combined.append(combined_row)
            else:
                # Film with no sessions found
                combined_row = film.copy()
                combined_row.update({
                    'session_date': '',
                    'session_venue': '',
                    'session_time': '',
                    'session_context': 'No sessions found',
                })
                combined.append(combined_row)
        
        self.combined_data = combined
        print(f"Step 4 complete: {len(combined)} combined records created")
        return combined
    
    def save_all_data(self, base_filename='miff_2025'):
        """Save all the scraped data to multiple CSV files"""
        
        # Save film details
        if self.films_data:
            films_df = pd.DataFrame(self.films_data)
            films_filename = f"{base_filename}_films.csv"
            films_df.to_csv(films_filename, index=False)
            print(f"Saved {len(self.films_data)} films to {films_filename}")
        
        # Save session data
        if self.sessions_data:
            sessions_df = pd.DataFrame(self.sessions_data)
            sessions_filename = f"{base_filename}_sessions.csv"
            sessions_df.to_csv(sessions_filename, index=False)
            print(f"Saved {len(self.sessions_data)} sessions to {sessions_filename}")
        
        # Save combined data
        if self.combined_data:
            combined_df = pd.DataFrame(self.combined_data)
            combined_filename = f"{base_filename}_complete.csv"
            combined_df.to_csv(combined_filename, index=False)
            print(f"Saved {len(self.combined_data)} combined records to {combined_filename}")
            
            # Create a summary with key columns
            summary_cols = ['title', 'director', 'year', 'runtime', 'countries', 'genres', 
                          'premiere_status', 'session_date', 'session_venue', 'session_time', 'film_url']
            summary_df = combined_df[summary_cols].copy()
            summary_filename = f"{base_filename}_summary.csv"
            summary_df.to_csv(summary_filename, index=False)
            print(f"Saved summary to {summary_filename}")
            
            return combined_df
        
        return None
    
    def print_statistics(self):
        """Print summary statistics of the scraped data"""
        print("\n" + "="*60)
        print("MIFF 2025 SCRAPING SUMMARY")
        print("="*60)
        
        print(f"Films scraped: {len(self.films_data)}")
        print(f"Sessions found: {len(self.sessions_data)}")
        print(f"Combined records: {len(self.combined_data)}")
        
        if self.films_data:
            films_with_directors = len([f for f in self.films_data if f['director']])
            films_with_descriptions = len([f for f in self.films_data if f['description']])
            print(f"Films with directors: {films_with_directors}")
            print(f"Films with descriptions: {films_with_descriptions}")
        
        if self.sessions_data:
            # Venue statistics
            venues = {}
            for session in self.sessions_data:
                venue = session['venue']
                venues[venue] = venues.get(venue, 0) + 1
            
            print(f"\nSessions by venue:")
            for venue, count in sorted(venues.items(), key=lambda x: x[1], reverse=True):
                print(f"  {venue}: {count}")
        
        if self.combined_data:
            films_with_sessions = len([r for r in self.combined_data if r['session_venue']])
            films_without_sessions = len(self.combined_data) - films_with_sessions
            
            print(f"\nFilms with sessions: {films_with_sessions}")
            print(f"Films without sessions: {films_without_sessions}")
        
        print("\nSample films:")
        for i, film in enumerate(self.films_data[:3]):
            print(f"{i+1}. {film['title']} ({film['year']}) - {film['director']}")
    
    def run_complete_scrape(self):
        """Run the complete scraping process"""
        
        print("MIFF 2025 Complete Scraper")
        print("This will scrape film details AND session schedules")
        print("=" * 60)
        
        try:
            # Step 1 & 2: Get all films
            films = self.scrape_all_films()
            
            # Step 3: Get all sessions
            sessions = self.scrape_all_sessions()
            
            # Step 4: Combine them
            combined = self.combine_films_and_sessions()
            
            # Step 5: Save everything
            df = self.save_all_data()
            
            # Step 6: Show statistics
            self.print_statistics()
            
            print(f"\n✅ Scraping complete! Check the generated CSV files.")
            
            return df
            
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            return None

# Quick test function
def test_single_schedule_page():
    """Test scraping a single schedule page to see the structure"""
    
    scraper = CompleteMIFFScraper()
    print("Testing single schedule page structure...")
    
    # Test the opening day
    test_date = "2025-08-07"
    sessions = scraper.scrape_schedule_for_date(test_date)
    
    print(f"Found {len(sessions)} sessions for {test_date}")
    for i, session in enumerate(sessions[:5]):  # Show first 5
        print(f"{i+1}. {session['film_title']} | {session['venue']} | {session['time']}")
    
    return sessions

# Usage
if __name__ == "__main__":
    
    # Option 1: Test a single schedule page first
    print("Option 1: Test single page")
    print("-" * 30)
    test_sessions = test_single_schedule_page()
    
    print("\n" + "="*60)
    
    # Option 2: Run complete scraping
    response = input("Run complete scraping? This will take 15-30 minutes. (y/n): ")
    
    if response.lower() == 'y':
        scraper = CompleteMIFFScraper()
        result = scraper.run_complete_scrape()
    else:
        print("Skipping complete scrape. Use the test results above to refine the approach.")