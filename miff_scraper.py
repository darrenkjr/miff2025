import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin

class SimplifiedMIFFScraper:
    
    def __init__(self):
        self.base_url = "https://miff.com.au"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.all_data = []
    
    def get_all_film_urls(self):
        print("Step 1: Discovering all films...")
        all_film_urls = set()
        
        for page in range(1, 25):
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
    
    def extract_sessions_from_film_page(self, soup, film_title):
        sessions = []
        
        try:
            ticketbox = soup.find('div', class_='ticketbox')
            if not ticketbox:
                return []
            
            session_rows = ticketbox.find_all('div', class_=re.compile(r'p-4.*text-xs.*lg:text-sm'))
            
            for row in session_rows:
                session_data = {
                    'session_date': '',
                    'session_time': '',
                    'session_venue': '',
                    'session_context': ''
                }
                
                date_elem = row.find('span', class_=re.compile(r'font-bold.*whitespace-nowrap'))
                if date_elem:
                    session_data['session_date'] = date_elem.get_text(strip=True)
                
                time_spans = row.find_all('span', class_=re.compile(r'whitespace-nowrap'))
                for span in time_spans:
                    text = span.get_text(strip=True)
                    if ':' in text and ('pm' in text.lower() or 'am' in text.lower()):
                        session_data['session_time'] = text
                        break
                
                mobile_venue = row.find('span', class_=re.compile(r'lg:hidden'))
                if mobile_venue and mobile_venue.get_text(strip=True):
                    venue_text = mobile_venue.get_text(strip=True)
                    if not any(word in venue_text.lower() for word in ['aug', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'sep', 'oct', 'nov', 'dec', ':', 'pm', 'am']):
                        session_data['session_venue'] = venue_text
                
                if not session_data['session_venue']:
                    desktop_venue_container = row.find('div', class_=re.compile(r'hidden.*lg:inline-block.*lg:col-span-3'))
                    if desktop_venue_container:
                        venue_div = desktop_venue_container.find('div')
                        if venue_div:
                            venue_text = venue_div.get_text(strip=True)
                            if venue_text and 'access' not in venue_text.lower():
                                session_data['session_venue'] = venue_text
                
                access_icons = row.find_all('span', class_='access_icon')
                if access_icons:
                    access_info = []
                    for icon in access_icons:
                        sr_only = icon.find('span', class_='sr-only')
                        if sr_only:
                            access_info.append(sr_only.get_text(strip=True))
                    if access_info:
                        session_data['session_context'] = 'Accessibility: ' + ', '.join(access_info)
                
                if session_data['session_date'] and session_data['session_time']:
                    sessions.append(session_data)
        
        except Exception as e:
            print(f"    Error extracting sessions: {e}")
        
        return sessions
    
    def scrape_film_with_sessions(self, film_url):
        try:
            response = self.session.get(film_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            film_data = {
                'film_url': film_url,
                'film_id': film_url.split('/')[-1],
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
            
            title_elem = soup.find('h1') or soup.select_one('.title, .film-title')
            if title_elem:
                film_data['title'] = title_elem.get_text(strip=True)
            
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
            
            page_text = soup.get_text()
            year_match = re.search(r'/\s*(\d{4})\s*/', page_text)
            if year_match:
                film_data['year'] = year_match.group(1)
            
            runtime_match = re.search(r'/\s*(\d+\s*mins?)\s*/', page_text)
            if runtime_match:
                film_data['runtime'] = runtime_match.group(1)
            
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
                film_data['synopsis'] = descriptions[1]

            
            quotes = []
            for elem in soup.find_all(['blockquote', 'q']):
                quote = elem.get_text(strip=True)
                if quote and len(quote) > 20:
                    quotes.append(quote)
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if '"' in text and ('–' in text or '—' in text) and len(text) > 30:
                    quotes.append(text)
            
            film_data['review_quotes'] = ' | '.join(quotes[:3])
            
            sessions = self.extract_sessions_from_film_page(soup, film_data['title'])
            
            combined_records = []
            if sessions:
                for session in sessions:
                    combined_record = film_data.copy()
                    combined_record.update(session)
                    combined_records.append(combined_record)
            else:
                combined_record = film_data.copy()
                combined_record.update({
                    'session_date': '',
                    'session_time': '',
                    'session_venue': '',
                    'session_context': 'No sessions found'
                })
                combined_records.append(combined_record)
            
            return combined_records
            
        except Exception as e:
            print(f"    Error scraping {film_url}: {e}")
            return []
    
    def scrape_all_films_and_sessions(self):
        print("Step 2: Scraping films and sessions...")
        film_urls = self.get_all_film_urls()
        
        for i, film_url in enumerate(film_urls, 1):
            print(f"  Scraping {i}/{len(film_urls)}: {film_url.split('/')[-1]}")
            
            combined_records = self.scrape_film_with_sessions(film_url)
            if combined_records:
                self.all_data.extend(combined_records)
                film_title = combined_records[0]['title']
                session_count = len([r for r in combined_records if r['session_time']])
                print(f"    ✓ {film_title} ({session_count} sessions)")
            
            time.sleep(1)
        
        print(f"Step 2 complete: {len(self.all_data)} records scraped")
        return self.all_data
    
    def save_data(self, filename='miff_2025_complete.csv'):
        if self.all_data:
            df = pd.DataFrame(self.all_data)
            df.to_csv(filename, index=False)
            print(f"Saved {len(self.all_data)} records to {filename}")
            
            summary_cols = ['title', 'director', 'year', 'runtime', 'genres', 'strands', 'description', 'synopsis', 'languages',
                          'session_date', 'session_venue', 'session_time', 'film_url']
            summary_df = df[summary_cols].copy()
            summary_filename = filename.replace('.csv', '_summary.csv')
            summary_df.to_csv(summary_filename, index=False)
            print(f"Saved summary to {summary_filename}")
            
            return df
        return None
    
    def print_statistics(self):
        print("\n" + "="*60)
        print("MIFF 2025 SCRAPER SUMMARY")
        print("="*60)
        
        print(f"Total records: {len(self.all_data)}")
        unique_films = len(set(record['title'] for record in self.all_data if record['title']))
        records_with_sessions = len([r for r in self.all_data if r['session_time']])
        
        print(f"Unique films: {unique_films}")
        print(f"Records with sessions: {records_with_sessions}")
        
        venues = {}
        for record in self.all_data:
            if record['session_venue']:
                venue = record['session_venue']
                venues[venue] = venues.get(venue, 0) + 1
        
        print(f"\nTop venues:")
        for venue, count in sorted(venues.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {venue}: {count}")
    
    def run_complete_scrape(self):
        print("MIFF 2025 Scraper")
        print("=" * 60)
        
        try:
            data = self.scrape_all_films_and_sessions()
            df = self.save_data()
            self.print_statistics()
            print(f"\n✅ Scraping complete!")
            return df
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return None

if __name__ == "__main__":
    scraper = SimplifiedMIFFScraper()
    result = scraper.run_complete_scrape()