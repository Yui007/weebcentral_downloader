#!/usr/bin/env python3
"""
Update Library Metadata Utility
Adds metadata to existing manga downloads that don't have .metadata.json files.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weebcentral_scraper import WeebCentralScraper


def get_downloads_directory() -> Path:
    """Get the downloads directory from settings or use default."""
    try:
        from gui.config import get_settings
        settings = get_settings()
        return Path(settings.output_dir)
    except:
        return Path("downloads")


def scan_library_for_missing_metadata(downloads_dir: Path) -> list:
    """Scan library and find manga without metadata."""
    missing_metadata = []
    
    if not downloads_dir.exists():
        print(f"❌ Downloads directory not found: {downloads_dir}")
        return missing_metadata
    
    for manga_dir in downloads_dir.iterdir():
        if not manga_dir.is_dir():
            continue
        
        metadata_file = manga_dir / '.metadata.json'
        if not metadata_file.exists():
            # Count chapters
            chapters = [d for d in manga_dir.iterdir() if d.is_dir()]
            missing_metadata.append({
                'path': manga_dir,
                'title': manga_dir.name,
                'chapter_count': len(chapters)
            })
    
    return missing_metadata


def fetch_metadata_from_url(url: str) -> Optional[Dict]:
    """Fetch manga metadata from WeebCentral URL."""
    print(f"🔍 Fetching metadata from: {url}")
    
    try:
        scraper = WeebCentralScraper(
            manga_url=url,
            output_dir="temp_metadata_fetch"
        )
        
        # Get manga info
        response = scraper._fetch_html(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract metadata
        metadata = {
            'url': url,
            'title': scraper.get_manga_title(soup),
            'description': '',
            'cover_url': '',
            'tags': [],
            'metadata': {}
        }
        
        # Try to get description
        desc_elem = soup.select_one('div.prose, div.description, p.description')
        if desc_elem:
            metadata['description'] = desc_elem.get_text(strip=True)
        
        # Try to get cover
        cover_elem = soup.select_one('img.cover, img.manga-cover, img[alt*="cover"]')
        if cover_elem and cover_elem.get('src'):
            metadata['cover_url'] = cover_elem['src']
        
        # Try to get tags
        tag_elems = soup.select('a.tag, span.tag, a.genre, span.genre')
        metadata['tags'] = [tag.get_text(strip=True) for tag in tag_elems]
        
        # Try to get additional metadata
        meta_items = soup.select('div.metadata dt, div.info-item')
        for item in meta_items:
            key = item.get_text(strip=True).rstrip(':')
            value_elem = item.find_next_sibling()
            if value_elem:
                metadata['metadata'][key] = value_elem.get_text(strip=True)
        
        print(f"✅ Successfully fetched metadata for: {metadata['title']}")
        return metadata
        
    except Exception as e:
        print(f"❌ Failed to fetch metadata: {e}")
        return None


def create_metadata_file(manga_dir: Path, metadata: Dict, download_cover: bool = True):
    """Create .metadata.json file for a manga."""
    import time
    
    metadata_file = manga_dir / '.metadata.json'
    
    # Add download date
    metadata['download_date'] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Count actual chapters
    chapters = [d for d in manga_dir.iterdir() if d.is_dir()]
    metadata['total_chapters'] = len(chapters)
    
    # Save metadata
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created metadata file: {metadata_file}")
    
    # Download cover if requested and URL available
    if download_cover and metadata.get('cover_url'):
        try:
            import requests
            cover_url = metadata['cover_url']
            
            # Determine extension
            ext = 'jpg'
            for possible_ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                if possible_ext in cover_url.lower():
                    ext = possible_ext.lstrip('.')
                    break
            
            cover_path = manga_dir / f'cover.{ext}'
            
            if not cover_path.exists():
                print(f"📥 Downloading cover image...")
                response = requests.get(cover_url, timeout=10)
                response.raise_for_status()
                
                with open(cover_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Downloaded cover: {cover_path}")
        except Exception as e:
            print(f"⚠️  Failed to download cover: {e}")


def create_manual_metadata(manga_dir: Path, title: str):
    """Create a basic metadata file with manual input."""
    print(f"\n📝 Creating metadata for: {title}")
    print("=" * 60)
    
    metadata = {
        'title': title,
        'url': '',
        'description': '',
        'tags': [],
        'metadata': {}
    }
    
    # Ask for URL
    url = input("Enter manga URL (or press Enter to skip): ").strip()
    if url:
        metadata['url'] = url
    
    # Ask for description
    print("\nEnter description (press Enter twice to finish):")
    desc_lines = []
    while True:
        line = input()
        if not line:
            break
        desc_lines.append(line)
    if desc_lines:
        metadata['description'] = ' '.join(desc_lines)
    
    # Ask for tags
    tags_input = input("\nEnter tags (comma-separated): ").strip()
    if tags_input:
        metadata['tags'] = [tag.strip() for tag in tags_input.split(',')]
    
    # Ask for additional info
    print("\nAdditional information (press Enter on key to finish):")
    while True:
        key = input("  Key (e.g., Author, Status): ").strip()
        if not key:
            break
        value = input(f"  {key}: ").strip()
        if value:
            metadata['metadata'][key] = value
    
    create_metadata_file(manga_dir, metadata, download_cover=False)


def interactive_mode(downloads_dir: Path):
    """Interactive mode to update metadata for each manga."""
    missing = scan_library_for_missing_metadata(downloads_dir)
    
    if not missing:
        print("✅ All manga already have metadata!")
        return
    
    print(f"\n📚 Found {len(missing)} manga without metadata:\n")
    for i, manga in enumerate(missing, 1):
        print(f"{i}. {manga['title']} ({manga['chapter_count']} chapters)")
    
    print("\n" + "=" * 60)
    print("Options:")
    print("1. Auto-fetch from URL (you'll provide URLs)")
    print("2. Manual entry (you'll enter details)")
    print("3. Skip (create basic metadata with just title)")
    print("=" * 60)
    
    for manga in missing:
        print(f"\n📖 Processing: {manga['title']}")
        print("-" * 60)
        
        choice = input("Choose option (1/2/3/skip): ").strip()
        
        if choice == '1':
            url = input("Enter manga URL: ").strip()
            if url:
                metadata = fetch_metadata_from_url(url)
                if metadata:
                    create_metadata_file(manga['path'], metadata)
                else:
                    print("⚠️  Failed to fetch. Skipping...")
        
        elif choice == '2':
            create_manual_metadata(manga['path'], manga['title'])
        
        elif choice == '3':
            metadata = {
                'title': manga['title'],
                'url': '',
                'description': '',
                'tags': [],
                'metadata': {}
            }
            create_metadata_file(manga['path'], metadata, download_cover=False)
        
        else:
            print("⏭️  Skipped")


def batch_mode_from_file(downloads_dir: Path, mapping_file: Path):
    """Batch update from a mapping file."""
    if not mapping_file.exists():
        print(f"❌ Mapping file not found: {mapping_file}")
        return
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    for folder_name, url in mappings.items():
        manga_dir = downloads_dir / folder_name
        
        if not manga_dir.exists():
            print(f"⚠️  Folder not found: {folder_name}")
            continue
        
        metadata_file = manga_dir / '.metadata.json'
        if metadata_file.exists():
            print(f"⏭️  Already has metadata: {folder_name}")
            continue
        
        print(f"\n📖 Processing: {folder_name}")
        metadata = fetch_metadata_from_url(url)
        
        if metadata:
            create_metadata_file(manga_dir, metadata)
        else:
            print(f"❌ Failed to fetch metadata for: {folder_name}")


def create_mapping_template(downloads_dir: Path):
    """Create a template mapping file for batch updates."""
    missing = scan_library_for_missing_metadata(downloads_dir)
    
    if not missing:
        print("✅ All manga already have metadata!")
        return
    
    template = {}
    for manga in missing:
        template[manga['title']] = "https://weebcentral.com/series/..."
    
    template_file = downloads_dir / 'url_mapping_template.json'
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created template: {template_file}")
    print("\n📝 Instructions:")
    print("1. Edit the file and replace URLs with actual manga URLs")
    print("2. Run: python update_library_metadata.py --batch url_mapping_template.json")


def main():
    parser = argparse.ArgumentParser(
        description="Update library metadata for existing manga downloads"
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode - update each manga one by one'
    )
    parser.add_argument(
        '--batch', '-b',
        type=str,
        metavar='FILE',
        help='Batch mode - use JSON mapping file (folder_name: url)'
    )
    parser.add_argument(
        '--create-template', '-t',
        action='store_true',
        help='Create a template mapping file for batch updates'
    )
    parser.add_argument(
        '--downloads-dir', '-d',
        type=str,
        help='Downloads directory (default: from settings or "downloads")'
    )
    
    args = parser.parse_args()
    
    # Get downloads directory
    if args.downloads_dir:
        downloads_dir = Path(args.downloads_dir)
    else:
        downloads_dir = get_downloads_directory()
    
    print("=" * 60)
    print("📚 WeebCentral Library Metadata Updater")
    print("=" * 60)
    print(f"Downloads directory: {downloads_dir}")
    print()
    
    if args.create_template:
        create_mapping_template(downloads_dir)
    
    elif args.batch:
        mapping_file = Path(args.batch)
        batch_mode_from_file(downloads_dir, mapping_file)
    
    elif args.interactive:
        interactive_mode(downloads_dir)
    
    else:
        # Show status and options
        missing = scan_library_for_missing_metadata(downloads_dir)
        
        if not missing:
            print("✅ All manga already have metadata!")
        else:
            print(f"📊 Found {len(missing)} manga without metadata:\n")
            for manga in missing:
                print(f"  • {manga['title']} ({manga['chapter_count']} chapters)")
            
            print("\n" + "=" * 60)
            print("Run with one of these options:")
            print("  --interactive    Update each manga interactively")
            print("  --create-template    Create a URL mapping template")
            print("  --batch FILE     Batch update from mapping file")
            print("=" * 60)


if __name__ == "__main__":
    main()
