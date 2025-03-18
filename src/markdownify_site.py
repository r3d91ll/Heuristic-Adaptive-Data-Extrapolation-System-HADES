#!/usr/bin/env python3
"""
Script to markdownify an entire website by crawling links
"""

import os
import sys
import re
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import argparse
import pathvalidate
import urllib.parse

def markdownify_url(url, output_path, base_url=None):
    """
    Fetch a URL, convert its HTML to Markdown, and save to output_path
    Returns list of links found in the page
    """
    try:
        print(f"Fetching URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        print(f"Converting to Markdown...")
        html = response.text
        soup = BeautifulSoup(html, features="html.parser")
        
        # Get all links for crawling
        links = []
        if base_url:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                # Filter out external links and anchors
                if href.startswith(('http://', 'https://')):
                    # Only include links to the same domain
                    if base_url in href and href.endswith('.html'):
                        links.append(href)
                elif not href.startswith(('mailto:', 'tel:', '#', 'javascript:')):
                    # Handle relative URLs
                    if href.endswith('.html'):
                        absolute_url = urllib.parse.urljoin(url, href)
                        links.append(absolute_url)
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Convert to markdown
        markdown = md(str(soup), heading_style="ATX")
        
        # Sanitize output path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
            
        print(f"Markdown saved to: {output_path}")
        return links
        
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

def crawl_site(start_url, output_dir, max_pages=20):
    """
    Crawl a site starting from start_url and save markdown to output_dir
    """
    visited = set()
    to_visit = [start_url]
    count = 0
    
    parsed_url = urllib.parse.urlparse(start_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    base_path = os.path.dirname(parsed_url.path)
    
    while to_visit and count < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
            
        visited.add(url)
        
        # Determine output path
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # Handle the base URL specially
        if path.endswith('/') or path == "":
            filename = "index"
        else:
            # Extract just the filename without extension
            filename = os.path.basename(path).replace('.html', '')
        
        # Get the directory part relative to the base
        dir_path = os.path.dirname(path)
        if base_path and dir_path.startswith(base_path):
            dir_path = dir_path[len(base_path):].lstrip('/')
        
        # Create the final output path
        if dir_path:
            rel_dir = os.path.join(output_dir, dir_path)
            os.makedirs(rel_dir, exist_ok=True)
            output_file = os.path.join(rel_dir, f"{filename}.md")
        else:
            output_file = os.path.join(output_dir, f"{filename}.md")
        
        # Markdownify and get new links
        links = markdownify_url(url, output_file, base_url)
        count += 1
        
        # Add new links to visit
        for link in links:
            if link not in visited and link.startswith(base_url):
                to_visit.append(link)
    
    print(f"Crawled {count} pages")
    return count

def main():
    parser = argparse.ArgumentParser(description="Convert website to markdown")
    parser.add_argument("url", help="Starting URL to convert to markdown")
    parser.add_argument("output_dir", help="Output directory path")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum number of pages to crawl")
    
    args = parser.parse_args()
    
    success = crawl_site(args.url, args.output_dir, args.max_pages)
    return 0 if success > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
