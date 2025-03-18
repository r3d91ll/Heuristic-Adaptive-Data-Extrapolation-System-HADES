#!/usr/bin/env python3
"""
Script to markdownify a webpage and save it to a local file
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import argparse
import pathvalidate

def markdownify_url(url, output_path):
    """
    Fetch a URL, convert its HTML to Markdown, and save to output_path
    """
    try:
        print(f"Fetching URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        print(f"Converting to Markdown...")
        html = response.text
        soup = BeautifulSoup(html, features="html.parser")
        
        # Remove script and style elements that we don't want to convert
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Optional: Extract only main content area if known
        # main_content = soup.find("div", {"class": "main-content"})
        # content_html = str(main_content) if main_content else html
        
        # Convert to markdown
        markdown = md(str(soup), heading_style="ATX")
        
        # Sanitize output path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
            
        print(f"Markdown saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert webpage to markdown")
    parser.add_argument("url", help="URL to convert to markdown")
    parser.add_argument("output", help="Output file path")
    
    args = parser.parse_args()
    
    success = markdownify_url(args.url, args.output)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
