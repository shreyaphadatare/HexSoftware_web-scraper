import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
import time
from urllib.parse import urljoin, urlparse
import webbrowser

class EcommerceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.data = []
        self.running = False
        
    def scrape_books_toscrape(self, max_pages=1, max_products=None, callback=None):
        """Scrape books.toscrape.com"""
        self.running = True
        self.data = []
        base_url = "https://books.toscrape.com/"
        current_url = base_url
        page_count = 0
        
        try:
            while current_url and page_count < max_pages and self.running:
                if callback:
                    callback(f"📄 Fetching page {page_count + 1}: {current_url}")
                
                html = self._fetch_page(current_url)
                if not html:
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find all book articles
                books = soup.find_all('article', class_='product_pod')
                
                for book in books:
                    if max_products and len(self.data) >= max_products:
                        break
                    
                    book_data = self._extract_book_data(book, base_url)
                    if book_data:
                        self.data.append(book_data)
                        if callback:
                            title = book_data.get('title', 'Unknown')[:40]
                            callback(f"✅ Scraped: {title}...")
                
                # Find next page
                next_link = soup.find('li', class_='next')
                if next_link and next_link.find('a'):
                    next_url = urljoin(current_url, next_link.find('a')['href'])
                    current_url = next_url
                    page_count += 1
                    
                    if self.running:
                        time.sleep(1)  # Polite delay
                else:
                    current_url = None
        
        except Exception as e:
            if callback:
                callback(f"❌ Error: {str(e)}")
        
        return self.data
    
    def scrape_custom_site(self, url, max_pages=1, max_products=None, callback=None):
        """Scrape custom e-commerce site"""
        self.running = True
        self.data = []
        current_url = url
        page_count = 0
        
        try:
            while current_url and page_count < max_pages and self.running:
                if callback:
                    callback(f"📄 Fetching page {page_count + 1}: {current_url}")
                
                html = self._fetch_page(current_url)
                if not html:
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Try to find products using common selectors
                products = self._find_products(soup)
                
                for product in products:
                    if max_products and len(self.data) >= max_products:
                        break
                    
                    product_data = self._extract_general_product_data(product, current_url)
                    if product_data:
                        self.data.append(product_data)
                        if callback:
                            title = product_data.get('title', 'Unknown')[:40]
                            callback(f"✅ Scraped: {title}...")
                
                # Try to find next page
                next_url = self._find_next_page_general(soup, current_url)
                current_url = next_url
                page_count += 1
                
                if next_url and self.running:
                    time.sleep(1)
        
        except Exception as e:
            if callback:
                callback(f"❌ Error: {str(e)}")
        
        return self.data
    
    def _fetch_page(self, url):
        """Fetch webpage with error handling"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _extract_book_data(self, book_element, base_url):
        """Extract data from book element"""
        try:
            data = {
                'title': 'N/A',
                'price': 'N/A',
                'rating': 'N/A',
                'availability': 'N/A',
                'url': 'N/A',
                'image_url': 'N/A',
                'category': 'N/A',
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'books.toscrape.com'
            }
            
            # Extract title
            title_elem = book_element.find('h3')
            if title_elem:
                link = title_elem.find('a')
                if link:
                    data['title'] = link.get('title', link.text.strip())
                    if link.get('href'):
                        data['url'] = urljoin(base_url, link['href'])
            
            # Extract price
            price_elem = book_element.find('p', class_='price_color')
            if price_elem:
                data['price'] = price_elem.text.strip()
            
            # Extract rating
            rating_elem = book_element.find('p', class_=lambda x: x and 'star-rating' in x)
            if rating_elem:
                for class_name in rating_elem.get('class', []):
                    if class_name != 'star-rating':
                        data['rating'] = class_name
                        break
            
            # Extract availability
            availability_elem = book_element.find('p', class_='instock')
            if availability_elem:
                stock_text = availability_elem.text.strip()
                data['availability'] = stock_text
            
            # Extract image
            img_elem = book_element.find('img')
            if img_elem and img_elem.get('src'):
                data['image_url'] = urljoin(base_url, img_elem['src'])
                data['image_alt'] = img_elem.get('alt', 'N/A')
            
            # Try to get more details from individual book page
            if data['url'] != 'N/A':
                self._get_book_details(data)
            
            return data
        
        except Exception as e:
            print(f"Error extracting book data: {e}")
            return None
    
    def _get_book_details(self, book_data):
        """Get additional details from book page"""
        try:
            html = self._fetch_page(book_data['url'])
            if not html:
                return
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Description
            desc_elem = soup.find('div', id='product_description')
            if desc_elem:
                next_p = desc_elem.find_next_sibling('p')
                if next_p:
                    book_data['description'] = next_p.text.strip()[:200]
            
            # Product information table
            table = soup.find('table', class_='table-striped')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        key = th.text.strip().lower().replace(' ', '_')
                        value = td.text.strip()
                        book_data[key] = value
            
            # Category
            breadcrumb = soup.find('ul', class_='breadcrumb')
            if breadcrumb:
                links = breadcrumb.find_all('a')
                if len(links) >= 2:
                    book_data['category'] = links[1].text.strip()
        
        except Exception as e:
            print(f"Error getting book details: {e}")
    
    def _find_products(self, soup):
        """Try to find products on a page"""
        # Common product selectors
        selectors = [
            'article.product',
            'div.product',
            'li.product',
            'article',
            'div[class*="product"]',
            'li[class*="product"]',
            'div[class*="item"]',
            'li[class*="item"]',
            'div.product-item',
            'li.product-item'
        ]
        
        for selector in selectors:
            products = soup.select(selector)
            if products:
                return products
        
        # If no products found with selectors, look for product-like structures
        products = []
        for elem in soup.find_all(['div', 'article', 'li']):
            if elem.find(['h1', 'h2', 'h3', 'h4']) and elem.find(text=lambda x: '$' in str(x) or '£' in str(x)):
                products.append(elem)
        
        return products
    
    def _extract_general_product_data(self, element, base_url):
        """Extract data from general product element"""
        try:
            data = {
                'title': 'N/A',
                'price': 'N/A',
                'url': 'N/A',
                'image_url': 'N/A',
                'description': 'N/A',
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': base_url
            }
            
            # Try to find title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.name'])
            if title_elem:
                data['title'] = title_elem.text.strip()
                link = title_elem.find('a')
                if link and link.get('href'):
                    data['url'] = urljoin(base_url, link['href'])
            
            # Try to find price
            price_text = element.find(text=lambda x: '$' in str(x) or '£' in str(x) or '€' in str(x))
            if price_text:
                data['price'] = price_text.strip()
            else:
                price_elem = element.find(['.price', '.cost', '.amount', '[class*="price"]'])
                if price_elem:
                    data['price'] = price_elem.text.strip()
            
            # Try to find image
            img_elem = element.find('img')
            if img_elem and img_elem.get('src'):
                data['image_url'] = urljoin(base_url, img_elem['src'])
            
            # Try to find description
            desc_elem = element.find('p')
            if desc_elem:
                data['description'] = desc_elem.text.strip()[:100]
            
            return data
        
        except Exception as e:
            print(f"Error extracting product data: {e}")
            return None
    
    def _find_next_page_general(self, soup, current_url):
        """Find next page URL for general sites"""
        # Common next page selectors
        next_selectors = [
            'a[rel="next"]',
            '.next a',
            '.pagination a:last-child',
            '[class*="next"] a',
            'a:contains("Next")',
            'a:contains("next")'
        ]
        
        for selector in next_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.get('href'):
                    return urljoin(current_url, next_link['href'])
            except:
                pass
        
        # Look for next button
        for link in soup.find_all('a'):
            if link.text and 'next' in link.text.lower():
                if link.get('href'):
                    return urljoin(current_url, link['href'])
        
        return None

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📚 Book Scraper Pro")
        self.root.geometry("1000x700")
        
        # Colors
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'light': '#ecf0f1',
            'dark': '#2c3e50'
        }
        
        self.setup_ui()
        self.scraper = EcommerceScraper()
        self.log_queue = queue.Queue()
        self.check_log_queue()
        
    def setup_ui(self):
        """Setup the GUI interface"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(main_container, bg=self.colors['primary'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="📚 E-COMMERCE WEB SCRAPER", 
                              font=('Arial', 18, 'bold'), 
                              fg='white', bg=self.colors['primary'])
        title_label.pack(pady=15)
        
        # Content frame
        content_frame = tk.Frame(main_container, bg=self.colors['light'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Controls
        left_panel = tk.Frame(content_frame, bg=self.colors['light'], width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Site selection
        site_frame = tk.LabelFrame(left_panel, text="Website Selection", 
                                  font=('Arial', 10, 'bold'),
                                  bg=self.colors['light'], padx=10, pady=10)
        site_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.site_var = tk.StringVar(value="books.toscrape.com")
        
        tk.Radiobutton(site_frame, text="📚 Books.toscrape.com", 
                      variable=self.site_var, value="books.toscrape.com",
                      bg=self.colors['light'], font=('Arial', 9)).pack(anchor=tk.W, pady=2)
        
        tk.Radiobutton(site_frame, text="🌐 Custom Website", 
                      variable=self.site_var, value="custom",
                      bg=self.colors['light'], font=('Arial', 9)).pack(anchor=tk.W, pady=2)
        
        self.custom_url_entry = tk.Entry(site_frame, font=('Arial', 9))
        self.custom_url_entry.pack(fill=tk.X, pady=5)
        self.custom_url_entry.insert(0, "https://")
        
        # Settings frame
        settings_frame = tk.LabelFrame(left_panel, text="Scraping Settings", 
                                      font=('Arial', 10, 'bold'),
                                      bg=self.colors['light'], padx=10, pady=10)
        settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Max pages
        tk.Label(settings_frame, text="Max Pages:", 
                bg=self.colors['light'], font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_pages = tk.Spinbox(settings_frame, from_=1, to=50, width=10, font=('Arial', 9))
        self.max_pages.delete(0, tk.END)
        self.max_pages.insert(0, "3")
        self.max_pages.grid(row=0, column=1, padx=(10, 0), pady=5)
        
        # Max products
        tk.Label(settings_frame, text="Max Products:", 
                bg=self.colors['light'], font=('Arial', 9)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_products = tk.Spinbox(settings_frame, from_=1, to=1000, width=10, font=('Arial', 9))
        self.max_products.delete(0, tk.END)
        self.max_products.insert(0, "50")
        self.max_products.grid(row=1, column=1, padx=(10, 0), pady=5)
        
        # Buttons frame
        button_frame = tk.Frame(left_panel, bg=self.colors['light'])
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = tk.Button(button_frame, text="▶ START SCRAPING", 
                                  font=('Arial', 10, 'bold'),
                                  bg=self.colors['secondary'], fg='white',
                                  relief=tk.RAISED, padx=20, pady=10,
                                  command=self.start_scraping)
        self.start_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.stop_btn = tk.Button(button_frame, text="⏹ STOP", 
                                 font=('Arial', 10),
                                 bg=self.colors['danger'], fg='white',
                                 relief=tk.RAISED, padx=20, pady=10,
                                 command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.export_btn = tk.Button(button_frame, text="💾 EXPORT DATA", 
                                   font=('Arial', 10),
                                   bg=self.colors['success'], fg='white',
                                   relief=tk.RAISED, padx=20, pady=10,
                                   command=self.export_data, state=tk.DISABLED)
        self.export_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Progress
        self.progress = ttk.Progressbar(left_panel, mode='indeterminate', length=280)
        self.progress.pack(pady=(20, 10))
        
        # Status
        self.status_var = tk.StringVar(value="Ready to scrape")
        status_label = tk.Label(left_panel, textvariable=self.status_var,
                               font=('Arial', 9, 'italic'),
                               fg=self.colors['dark'], bg=self.colors['light'])
        status_label.pack()
        
        # Right panel - Output
        right_panel = tk.Frame(content_frame, bg=self.colors['light'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Log tab
        log_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(log_frame, text="📝 Log")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                 font=('Consolas', 9),
                                                 bg='#f8f9fa', fg=self.colors['dark'])
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Data tab
        data_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(data_frame, text="📊 Data")
        
        # Treeview for data display
        columns = ('#', 'Title', 'Price', 'Rating', 'Category')
        self.tree = ttk.Treeview(data_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        tree_scroll = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Preview tab
        preview_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(preview_frame, text="👁 Preview")
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD,
                                                     font=('Consolas', 9),
                                                     bg='#f8f9fa', fg=self.colors['dark'])
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Stats tab
        stats_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(stats_frame, text="📈 Statistics")
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD,
                                                   font=('Consolas', 9),
                                                   bg='#f8f9fa', fg=self.colors['dark'])
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_queue.put(formatted_message)
    
    def check_log_queue(self):
        """Check for new log messages"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END)
                self.log_text.update()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_log_queue)
    
    def start_scraping(self):
        """Start scraping in separate thread"""
        if self.scraper.running:
            return
        
        # Get settings
        try:
            max_pages = int(self.max_pages.get())
            max_products = int(self.max_products.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for settings")
            return
        
        # Get URL
        site_choice = self.site_var.get()
        if site_choice == "custom":
            url = self.custom_url_entry.get().strip()
            if not url or url == "https://":
                messagebox.showwarning("Warning", "Please enter a valid URL")
                return
        else:
            url = site_choice
        
        # Update UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.status_var.set("Scraping...")
        
        # Clear previous data
        self.tree.delete(*self.tree.get_children())
        self.preview_text.delete(1.0, tk.END)
        self.stats_text.delete(1.0, tk.END)
        self.log_text.delete(1.0, tk.END)
        
        # Start scraping thread
        thread = threading.Thread(
            target=self._scrape_thread,
            args=(url, max_pages, max_products, site_choice),
            daemon=True
        )
        thread.start()
    
    def _scrape_thread(self, url, max_pages, max_products, site_choice):
        """Thread function for scraping"""
        self.log_message(f"🚀 Starting scrape: {url}")
        self.log_message(f"⚙️ Settings: {max_pages} pages, {max_products} max products")
        
        if site_choice == "books.toscrape.com":
            data = self.scraper.scrape_books_toscrape(
                max_pages=max_pages,
                max_products=max_products,
                callback=self.log_message
            )
        else:
            data = self.scraper.scrape_custom_site(
                url=url,
                max_pages=max_pages,
                max_products=max_products,
                callback=self.log_message
            )
        
        # Update UI in main thread
        self.root.after(0, self._scraping_complete, data)
    
    def _scraping_complete(self, data):
        """Handle scraping completion"""
        self.progress.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if data:
            self.export_btn.config(state=tk.NORMAL)
            self.status_var.set(f"✅ Scraped {len(data)} items")
            
            # Update treeview
            for i, item in enumerate(data, 1):
                values = (
                    str(i),
                    item.get('title', 'N/A')[:40],
                    item.get('price', 'N/A'),
                    item.get('rating', 'N/A'),
                    item.get('category', 'N/A')
                )
                self.tree.insert('', tk.END, values=values)
            
            # Update preview with JSON
            preview_data = json.dumps(data[:3], indent=2, ensure_ascii=False)
            self.preview_text.insert(1.0, preview_data)
            
            # Generate statistics
            self._generate_statistics(data)
            
            self.log_message(f"✅ Scraping complete! {len(data)} items scraped.")
        else:
            self.status_var.set("❌ No data scraped")
            self.log_message("❌ No data was scraped.")
    
    def _generate_statistics(self, data):
        """Generate statistics from scraped data"""
        if not data:
            return
        
        stats = "📊 SCRAPING STATISTICS\n"
        stats += "=" * 50 + "\n\n"
        stats += f"Total Items: {len(data)}\n"
        
        # Price analysis
        prices = []
        for item in data:
            price_str = item.get('price', '')
            if price_str:
                # Extract numeric value
                import re
                match = re.search(r'[\d\.]+', price_str.replace('£', '').replace('$', '').replace(',', ''))
                if match:
                    try:
                        prices.append(float(match.group()))
                    except:
                        pass
        
        if prices:
            stats += f"\n💰 PRICE ANALYSIS:\n"
            stats += f"  Average Price: £{sum(prices)/len(prices):.2f}\n"
            stats += f"  Highest Price: £{max(prices):.2f}\n"
            stats += f"  Lowest Price: £{min(prices):.2f}\n"
            stats += f"  Total Value: £{sum(prices):.2f}\n"
        
        # Rating analysis
        ratings = {}
        for item in data:
            rating = item.get('rating', 'Unknown')
            ratings[rating] = ratings.get(rating, 0) + 1
        
        if ratings:
            stats += f"\n⭐ RATING DISTRIBUTION:\n"
            for rating, count in sorted(ratings.items()):
                stats += f"  {rating}: {count} items\n"
        
        # Category analysis
        categories = {}
        for item in data:
            category = item.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        if categories:
            stats += f"\n📚 CATEGORIES:\n"
            for category, count in sorted(categories.items()):
                stats += f"  {category}: {count} items\n"
        
        self.stats_text.insert(1.0, stats)
    
    def stop_scraping(self):
        """Stop the scraping process"""
        self.scraper.running = False
        self.log_message("⏹ Scraping stopped by user")
        self.status_var.set("Stopped")
    
    def export_data(self):
        """Export scraped data to file"""
        if not self.scraper.data:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        # Ask for file type
        file_types = [
            ("CSV files", "*.csv"),
            ("JSON files", "*.json"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"scraped_data_{timestamp}"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=file_types,
            initialfile=default_name
        )
        
        if not filename:
            return
        
        try:
            if filename.endswith('.csv'):
                self._export_csv(filename)
            elif filename.endswith('.json'):
                self._export_json(filename)
            else:
                self._export_txt(filename)
            
            self.log_message(f"✅ Data exported to: {filename}")
            messagebox.showinfo("Success", f"Data exported successfully!\n{filename}")
            
            # Ask to open folder
            response = messagebox.askyesno("Open Folder", "Open containing folder?")
            if response:
                folder_path = os.path.dirname(os.path.abspath(filename))
                webbrowser.open(folder_path)
            
        except Exception as e:
            self.log_message(f"❌ Export failed: {str(e)}")
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def _export_csv(self, filename):
        """Export to CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if self.scraper.data:
                # Get all fieldnames
                fieldnames = set()
                for item in self.scraper.data:
                    fieldnames.update(item.keys())
                
                fieldnames = sorted(fieldnames)
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.scraper.data)
    
    def _export_json(self, filename):
        """Export to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.scraper.data, f, indent=2, ensure_ascii=False)
    
    def _export_txt(self, filename):
        """Export to TXT"""
        with open(filename, 'w', encoding='utf-8') as f:
            for i, item in enumerate(self.scraper.data, 1):
                f.write(f"Item {i}:\n")
                f.write("-" * 40 + "\n")
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

def main():
    """Main function"""
    root = tk.Tk()
    app = ScraperGUI(root)
    
    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()