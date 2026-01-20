"""
URL Crawler Agent - Extracts text content from web pages
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse, urljoin
from typing import Dict, Optional, List


class UrlCrawler:
    """Agent for crawling and extracting text from web pages"""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Set a user agent to appear as a regular browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def crawl_url(self, url: str) -> Dict[str, any]:
        """
        Crawl a URL and extract its text content
        
        Args:
            url (str): The URL to crawl
            
        Returns:
            Dict with keys: success (bool), content (str), title (str), error (str)
        """
        try:
            # Validate URL
            if not self._is_valid_url(url):
                return {
                    'success': False,
                    'error': 'Invalid URL format',
                    'content': '',
                    'title': ''
                }
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            print(f"🔗 Crawling URL: {url}")
            
            # Make request with retries
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == self.max_retries - 1:
                        return {
                            'success': False,
                            'error': f'Failed to fetch URL after {self.max_retries} attempts: {str(e)}',
                            'content': '',
                            'title': ''
                        }
                    time.sleep(1)  # Brief pause before retry
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return {
                    'success': False,
                    'error': f'URL does not serve HTML content (Content-Type: {content_type})',
                    'content': '',
                    'title': ''
                }
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup, url)
            
            # Extract main content
            content = self._extract_content(soup)
            
            if not content or len(content.strip()) < 50:
                return {
                    'success': False,
                    'error': 'Could not extract meaningful content from the webpage',
                    'content': '',
                    'title': title
                }
            
            print(f"✅ Successfully extracted {len(content)} characters from {url}")
            
            return {
                'success': True,
                'content': content,
                'title': title,
                'error': ''
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error crawling URL: {str(e)}',
                'content': '',
                'title': ''
            }
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            # Add protocol if missing for validation
            test_url = url if url.startswith(('http://', 'https://')) else f'https://{url}'
            parsed = urlparse(test_url)
            return bool(parsed.netloc) and bool(parsed.scheme in ('http', 'https'))
        except:
            return False
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page title"""
        try:
            # Try title tag first
            title_tag = soup.find('title')
            if title_tag and title_tag.text.strip():
                return title_tag.text.strip()
            
            # Try h1 tag
            h1_tag = soup.find('h1')
            if h1_tag and h1_tag.text.strip():
                return h1_tag.text.strip()
            
            # Fallback to domain name
            domain = urlparse(url).netloc.replace('www.', '')
            return f"Content from {domain}"
            
        except:
            return "Webpage Content"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from HTML"""
        try:
            # Remove script, style, and other non-content elements (be more selective)
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Remove Wikipedia-specific clutter selectively
            for selector in ['.navbox', '.mbox']:
                for element in soup.select(selector):
                    element.decompose()
            
            # Try to find main content areas first
            main_content = None
            
            # Look for common content containers (Wikipedia-specific first)
            content_selectors = [
                '#mw-content-text .mw-parser-output',  # Wikipedia main article content
                '#mw-content-text',  # Wikipedia main content
                '.mw-parser-output',  # Wikipedia article content  
                '#content',  # Generic content
                'main', 'article', '[role="main"]', '.content', '.post-content',
                '.entry-content', '.article-content', '.post-body', '.content-body'
            ]
            
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.find('body')
            
            if not main_content:
                main_content = soup
            
            # Extract text and clean it
            text = main_content.get_text(separator=' ', strip=True)
            
            # Clean up the text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            print(f"❌ Error extracting content: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Trim leading/trailing whitespace
        text = text.strip()
        
        return text


# Global instance
url_crawler = UrlCrawler()