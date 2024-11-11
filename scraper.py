import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import feedgenerator
from datetime import datetime
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

async def scrape_announcements():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            logging.info("Starting to scrape announcements")
            await page.goto('https://www.ldsh.ilc.edu.tw/p/403-1015-25-1.php?Lang=zh-tw')
            
            await page.wait_for_selector('table.listTB')
            
            processed_announcements = set()
            scroll_count = 0
            max_scrolls = 10
            
            feed = feedgenerator.Rss201rev2Feed(
                title="LDSH Announcements",
                link="https://www.ldsh.ilc.edu.tw/",
                description="最新公告",
                language="zh-tw"
            )

            while scroll_count < max_scrolls:
                await page.evaluate("""
                    window.scrollTo(0, document.body.scrollHeight);
                    window.dispatchEvent(new Event('scroll'));
                """)
                
                await asyncio.sleep(2)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                announcements = soup.find_all('table', class_='listTB')
                current_processed = set()
                
                for table in announcements:
                    rows = table.find_all('tr')
                    for row in rows:
                        try:
                            tds = row.find_all('td')
                            if len(tds) >= 3:
                                title_element = tds[2].find('a')
                                if title_element:
                                    title = title_element.text.strip()
                                    link = title_element['href']
                                    if not link.startswith('http'):
                                        link = f"https://www.ldsh.ilc.edu.tw{link}"
                                    
                                    announcement_id = f"{title}:{link}"
                                    
                                    if announcement_id not in processed_announcements:
                                        processed_announcements.add(announcement_id)
                                        current_processed.add(announcement_id)
                                        
                                        date_str = tds[0].text.strip()
                                        try:
                                            pub_date = datetime.strptime(date_str, '%Y-%m-%d')
                                        except ValueError:
                                            pub_date = datetime.now()
                                        
                                        feed.add_item(
                                            title=title,
                                            link=link,
                                            description="",
                                            pubdate=pub_date
                                        )
                        except Exception as e:
                            logging.error(f"Error processing announcement: {e}")
                
                logging.info(f"Scroll {scroll_count + 1}: Found {len(current_processed)} new announcements, total: {len(processed_announcements)}")
                scroll_count += 1
            
            logging.info("Writing RSS feed to file")
            with open('ldsh_announcements.xml', 'w', encoding='utf-8') as f:
                f.write(feed.writeString('utf-8'))
            
            await browser.close()
            return len(processed_announcements)
            
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    try:
        total_announcements = asyncio.run(scrape_announcements())
        logging.info(f"Successfully processed {total_announcements} announcements in total")
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)