#!/usr/bin/env python3
"""
Unified script for preparing and ingesting documentation into HADES
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from glob import glob
from bs4 import BeautifulSoup
import markdownify
import time

def fetch_url(url):
    """Fetch a URL and return its content"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def convert_to_markdown(html_content, output_file=None):
    """Convert HTML content to Markdown and optionally save to file"""
    if not html_content:
        return None
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
    
    # Convert to markdown
    md_converter = markdownify.MarkdownConverter(heading_style="ATX")
    markdown_content = md_converter.convert_soup(soup)
    
    # Save to file if requested
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved markdown to {output_file}")
    
    return markdown_content

def prepare_document(markdown_file, domain="python-arango-docs"):
    """Prepare a document for ingestion into HADES"""
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract title from the first heading
        lines = content.split('\n')
        title = next((line.strip('# ') for line in lines if line.startswith('# ')), 
                     os.path.basename(markdown_file))
        
        # Create document structure
        doc_id = os.path.basename(markdown_file).replace('.md', '').replace(' ', '_').lower()
        document = {
            "id": doc_id,
            "title": title,
            "content": content,
            "source": f"file://{os.path.abspath(markdown_file)}",
            "metadata": {
                "type": "documentation",
                "domain": domain,
                "path": os.path.basename(markdown_file)
            }
        }
        
        return document
    except Exception as e:
        print(f"Error preparing {markdown_file}: {e}")
        return None

def ingest_to_hades(data_points, domain="python-arango-docs", batch_size=5, output_dir=None):
    """Ingest data into HADES knowledge graph via direct import or MCP client
    
    Args:
        data_points: List of document dictionaries to ingest
        domain: Domain name for the documents
        batch_size: Number of documents per batch
        output_dir: Directory to save batch files (defaults to data/staging/{domain})
    """
    total = len(data_points)
    batches = [data_points[i:i+batch_size] for i in range(0, total, batch_size)]
    
    # Set up staging directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    if output_dir is None:
        # Create domain-specific staging directory
        domain_safe = domain.replace('-', '_').replace(' ', '_').lower()
        output_dir = os.path.join(project_root, 'data', 'staging', domain_safe)
    
    # Ensure staging directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Ingesting {total} data points in {len(batches)} batches...")
    print(f"Staging directory: {output_dir}")
    
    # Try to use direct client if available
    sys.path.insert(0, project_root)
    client = None
    direct_import = False
    
    try:
        # Try to import the client directly
        from src.mcp.clients.pathrag import PathRAGClient
        client = PathRAGClient()
        direct_import = True
        print("Using direct PathRAG client for ingestion")
    except ImportError:
        print("Could not import PathRAGClient directly. Will save batches to files.")
    
    batch_files = []
    
    # Process all batches
    for i, batch in enumerate(batches, 1):
        try:
            # Save batch to file regardless of direct import capability
            batch_file = os.path.join(output_dir, f"batch_{i}_of_{len(batches)}.json")
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(batch, f, indent=2)
            batch_files.append(batch_file)
            print(f"Saved batch {i}/{len(batches)} to {batch_file}")
            
            # If direct import is available, use it
            if direct_import and client:
                try:
                    print(f"Ingesting batch {i}/{len(batches)} ({len(batch)} items)...")
                    result = client.ingest_data(batch, domain=domain)
                    print(f"Batch {i} result: {result}")
                except Exception as e:
                    print(f"Exception ingesting batch {i}: {e}")
                # Small delay between batches
                time.sleep(1)
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
    
    # If we couldn't use direct import, provide instructions
    if not direct_import or not client:
        print("\nTo ingest these batches into HADES, use the following steps:")
        print("1. In Windsurf, use the 'mcp0_ingest_data' tool with the content of each batch file")
        print(f"2. Set the domain parameter to '{domain}'")
        print("\nExample for the first batch:")
        if batch_files:
            print(f"   - Open the file: {batch_files[0]}")
            print("   - Copy the content")
            print("   - Use the following in Windsurf:")
            print("     ```")
            print("     mcp0_ingest_data:")
            print("       data: [PASTE CONTENT HERE]")
            print(f"       domain: {domain}")
            print("     ```")
    
    # Create a manifest file with metadata
    manifest = {
        "domain": domain,
        "total_documents": total,
        "batch_size": batch_size,
        "num_batches": len(batches),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "batch_files": batch_files,
        "direct_import_attempted": direct_import,
        "direct_import_succeeded": direct_import and client is not None
    }
    
    manifest_file = os.path.join(output_dir, "manifest.json")
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nCreated manifest file: {manifest_file}")
    
    print(f"Ingestion process completed for {total} data points")
    return True

def crawl_site(base_url, output_dir, max_pages=100, domain="docs"):
    """Crawl a website and convert pages to markdown"""
    visited = set()
    to_visit = [base_url]
    count = 0
    
    os.makedirs(output_dir, exist_ok=True)
    
    while to_visit and count < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        
        visited.add(url)
        count += 1
        
        print(f"Processing {count}/{max_pages}: {url}")
        
        html_content = fetch_url(url)
        if not html_content:
            continue
        
        # Parse the page
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Convert URL to filename
        if url.endswith('/'):
            url = url[:-1]
        
        page_name = url.split('/')[-1]
        if not page_name or page_name == base_url.split('/')[-1]:
            page_name = "index"
        
        if not page_name.endswith('.html'):
            page_name += '.md'
        else:
            page_name = page_name.replace('.html', '.md')
        
        output_file = os.path.join(output_dir, page_name)
        
        # Convert to markdown
        convert_to_markdown(html_content, output_file)
        
        # Find links to follow
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip external links, anchors, etc.
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
                
            # Handle relative URLs
            if not href.startswith('http'):
                if href.startswith('/'):
                    # Absolute path relative to domain
                    domain = '/'.join(base_url.split('/')[:3])
                    href = domain + href
                else:
                    # Relative to current page
                    href = os.path.dirname(url) + '/' + href
            
            # Only follow links within the same domain
            if base_url.split('/')[2] in href and href not in visited:
                to_visit.append(href)
    
    return visited

def main():
    parser = argparse.ArgumentParser(description="Prepare and ingest documentation into HADES")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Convert URL to markdown
    url_parser = subparsers.add_parser('convert-url', help='Convert a URL to markdown')
    url_parser.add_argument('url', help='URL to convert')
    url_parser.add_argument('--output', '-o', required=True, help='Output file')
    
    # Crawl a site
    crawl_parser = subparsers.add_parser('crawl', help='Crawl a website and convert to markdown')
    crawl_parser.add_argument('base_url', help='Base URL to start crawling from')
    crawl_parser.add_argument('--output-dir', '-o', required=True, help='Output directory')
    crawl_parser.add_argument('--max-pages', '-m', type=int, default=100, help='Maximum pages to crawl')
    crawl_parser.add_argument('--domain', '-d', default='documentation', help='Domain name for the docs')
    
    # Prepare documents for ingestion
    prepare_parser = subparsers.add_parser('prepare', help='Prepare markdown docs for ingestion')
    prepare_parser.add_argument('input_dir', help='Input directory with markdown files')
    prepare_parser.add_argument('--output', '-o', required=True, help='Output JSON file')
    prepare_parser.add_argument('--domain', '-d', default='documentation', help='Domain name for the docs')
    
    # Ingest documents
    ingest_parser = subparsers.add_parser('ingest', help='Ingest prepared docs into HADES')
    ingest_parser.add_argument('json_file', help='JSON file with prepared documents')
    ingest_parser.add_argument('--domain', '-d', default='documentation', help='Domain name for the docs')
    ingest_parser.add_argument('--batch-size', '-b', type=int, default=5, help='Batch size for ingestion')
    ingest_parser.add_argument('--output-dir', help='Directory to save batch files (defaults to data/staging/{domain})')
    
    # All in one: crawl, prepare, and ingest
    all_parser = subparsers.add_parser('all', help='Crawl, prepare and ingest in one step')
    all_parser.add_argument('base_url', help='Base URL to start crawling from')
    all_parser.add_argument('--output-dir', '-o', required=True, help='Output directory for markdown and staging files')
    all_parser.add_argument('--max-pages', '-m', type=int, default=100, help='Maximum pages to crawl')
    all_parser.add_argument('--domain', '-d', default='documentation', help='Domain name for the docs')
    all_parser.add_argument('--batch-size', '-b', type=int, default=5, help='Batch size for ingestion')
    
    args = parser.parse_args()
    
    if args.command == 'convert-url':
        html_content = fetch_url(args.url)
        if html_content:
            convert_to_markdown(html_content, args.output)
    
    elif args.command == 'crawl':
        crawl_site(args.base_url, args.output_dir, args.max_pages, args.domain)
    
    elif args.command == 'prepare':
        # Find all markdown files in the input directory
        markdown_files = glob(os.path.join(args.input_dir, '**/*.md'), recursive=True)
        print(f"Found {len(markdown_files)} markdown files")
        
        # Prepare documents
        documents = []
        for md_file in markdown_files:
            print(f"Preparing {md_file}")
            doc = prepare_document(md_file, args.domain)
            if doc:
                documents.append(doc)
                print(f"Prepared {doc['id']} for ingestion")
        
        # Save to JSON file
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2)
        print(f"Saved {len(documents)} documents to {args.output}")
    
    elif args.command == 'ingest':
        # Load documents from JSON file
        with open(args.json_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        print(f"Loaded {len(documents)} documents from {args.json_file}")
        
        # Ingest documents
        ingest_to_hades(documents, args.domain, args.batch_size, args.output_dir)
    
    elif args.command == 'all':
        # Create temporary directory for markdown files
        md_dir = os.path.join(args.output_dir, 'markdown')
        json_file = os.path.join(args.output_dir, 'documents.json')
        
        # Crawl site
        crawl_site(args.base_url, md_dir, args.max_pages, args.domain)
        
        # Find all markdown files in the markdown directory
        markdown_files = glob(os.path.join(md_dir, '**/*.md'), recursive=True)
        print(f"Found {len(markdown_files)} markdown files")
        
        # Prepare documents
        documents = []
        for md_file in markdown_files:
            print(f"Preparing {md_file}")
            doc = prepare_document(md_file, args.domain)
            if doc:
                documents.append(doc)
                print(f"Prepared {doc['id']} for ingestion")
        
        # Save to JSON file
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2)
        print(f"Saved {len(documents)} documents to {json_file}")
        
        # Ingest documents
        staging_dir = os.path.join(args.output_dir, 'staging') 
        ingest_to_hades(documents, args.domain, args.batch_size, staging_dir)
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
