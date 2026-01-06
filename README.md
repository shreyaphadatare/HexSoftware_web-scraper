
📚 E-commerce Web Scraper GUI

A user-friendly desktop application built with Python and Tkinter for scraping product data from e-commerce websites.

✨ Features
🌐 Multi-site Support: Scrape from books.toscrape.com or any custom e-commerce URL

🎛️ Customizable Settings: Control max pages and products to scrape

📊 Real-time Logging: Live log display with timestamps

📈 Data Visualization: Tabular data view with built-in statistics

💾 Export Options: Save data in CSV, JSON, or TXT format

⏸️ Stop Control: Pause scraping at any time

🖥️ Clean GUI: Intuitive interface with color-coded sections

🛠️ Installation
Clone the repository:

bash
git clone https://github.com/yourusername/ecommerce-scraper.git
cd ecommerce-scraper
Install required packages:

bash
pip install requests beautifulsoup4
🚀 Usage
Run the application:

bash
python web-scraper.py
Steps to Use:
Select Website: Choose between books.toscrape.com or enter a custom URL

Configure Settings: Set max pages and products to scrape

Start Scraping: Click "START SCRAPING" to begin

Monitor Progress: View logs and data in real-time

Export Data: Save your scraped data in preferred format

📁 Project Structure
text
web-scraper.py          # Main application file
requirements.txt        # Python dependencies
README.md              # Documentation
⚙️ Dependencies
requests - HTTP requests

beautifulsoup4 - HTML parsing

tkinter - GUI framework (built-in)

📋 Features in Detail
Multi-threaded Scraping: Non-blocking UI during scraping

Error Handling: Robust error handling with user feedback

Data Validation: Clean and structured data extraction

Statistics Generation: Automatic price, rating, and category analysis

Preview Mode: View sample data before exporting
