#!/usr/bin/env python3
"""
Unified Music Library Management System
=======================================
A comprehensive web interface that combines all music library management tools
into one unified application.

Features:
- Add new music files
- Scan and export library
- Duplicate detection and management
- Configuration management
- Real-time library browsing
- File operations (move, delete, organize)
- Statistics and reporting
"""

import os
import sys
import json
import hashlib
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import quote, unquote

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
    from flask_cors import CORS
    import mutagen
    from PIL import Image
    import io
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please run: pip install flask flask-cors mutagen pillow")
    sys.exit(1)

# Configuration
CONFIG = {
    'library_path': '../Library',
    'new_path': '../New',
    'duplicate_path': '../Duplicate',
    'trash_path': '../Trash',
    'json_file': 'mayi-music-list.json',  # JSON file in current directory
    'thumbnails_dir': 'thumbnails',  # Save thumbnails in the current scripts directory
    'supported_formats': {'.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg', '.wma'},
    'max_workers': 4,
    'log_file': 'music_library.log'  # Log file in current directory
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG['log_file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CORS(app)

class MusicLibraryManager:
    """Unified music library management class"""
    
    def __init__(self):
        self.ensure_directories()
        self.load_catalog()
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for path in [CONFIG['library_path'], CONFIG['new_path'], 
                    CONFIG['duplicate_path'], CONFIG['trash_path']]:
            Path(path).mkdir(parents=True, exist_ok=True)
        
        # Create thumbnails directory
        Path(CONFIG['thumbnails_dir']).mkdir(parents=True, exist_ok=True)
    
    def load_catalog(self):
        """Load the music catalog from JSON file"""
        try:
            if os.path.exists(CONFIG['json_file']):
                with open(CONFIG['json_file'], 'r', encoding='utf-8') as f:
                    self.catalog = json.load(f)
            else:
                self.catalog = {'songs': [], 'last_updated': None}
        except Exception as e:
            logger.error(f"Error loading catalog: {e}")
            self.catalog = {'songs': [], 'last_updated': None}
    
    def save_catalog(self):
        """Save the music catalog to JSON file"""
        try:
            self.catalog['last_updated'] = datetime.now().isoformat()
            with open(CONFIG['json_file'], 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            logger.info(f"Catalog saved successfully to {CONFIG['json_file']} with {len(self.catalog['songs'])} songs")
        except Exception as e:
            logger.error(f"Error saving catalog: {e}")
            raise
    
    def get_file_hash(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def extract_metadata(self, file_path):
        """Extract metadata from music file"""
        try:
            audio = mutagen.File(file_path)
            if audio is None:
                return {}
            
            metadata = {}
            
            # Basic file info
            metadata['file_path'] = str(file_path)
            metadata['file_size'] = os.path.getsize(file_path)
            metadata['file_hash'] = self.get_file_hash(file_path)
            
            # Audio metadata
            if hasattr(audio, 'info'):
                metadata['duration'] = int(audio.info.length) if hasattr(audio.info, 'length') else None
                metadata['bitrate'] = audio.info.bitrate if hasattr(audio.info, 'bitrate') else None
                metadata['sample_rate'] = audio.info.sample_rate if hasattr(audio.info, 'sample_rate') else None
            
            # Tags
            if hasattr(audio, 'tags'):
                tags = audio.tags
                if tags:
                    # Common tag fields
                    tag_fields = ['title', 'artist', 'album', 'tracknumber', 'date', 'genre']
                    for field in tag_fields:
                        if field in tags:
                            value = tags[field]
                            if isinstance(value, list):
                                value = value[0]
                            metadata[field] = str(value)
            
            # Fallback to filename if no title
            if 'title' not in metadata or not metadata['title']:
                metadata['title'] = Path(file_path).stem
            
            # Extract thumbnail
            thumbnail_extracted = self.extract_thumbnail(file_path, audio)
            metadata['has_thumbnail'] = thumbnail_extracted
            
            # Add base64 thumbnail data if available
            if thumbnail_extracted:
                thumbnail_base64 = self.get_thumbnail_base64(file_path)
                if thumbnail_base64:
                    metadata['thumbnail_base64'] = thumbnail_base64
            
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            # Re-raise the exception so the calling method can handle it
            raise Exception(f"Failed to extract metadata from {Path(file_path).name}: {e}")
    
    def extract_thumbnail(self, file_path, audio):
        """Extract thumbnail from audio file"""
        try:
            # Get the filename without extension for thumbnail naming
            filename_stem = Path(file_path).stem
            thumbnail_path = Path(CONFIG['thumbnails_dir']) / f"{filename_stem}.jpg"
            
            # Check if thumbnail already exists
            if thumbnail_path.exists():
                logger.info(f"Thumbnail already exists for {filename_stem}")
                return True
            
            # Extract artwork from different tag formats
            artwork = None
            
            # Try different tag formats
            if hasattr(audio, 'tags'):
                tags = audio.tags
                
                # MP3/ID3 tags
                if hasattr(tags, 'getall'):
                    for key in ['APIC:', 'APIC:cover', 'APIC:0']:
                        try:
                            artwork_data = tags.getall(key)
                            if artwork_data:
                                artwork = artwork_data[0]
                                break
                        except:
                            continue
                
                # FLAC/Vorbis tags
                elif hasattr(tags, 'get'):
                    for key in ['metadata_block_picture', 'METADATA_BLOCK_PICTURE']:
                        try:
                            artwork_data = tags.get(key)
                            if artwork_data:
                                if isinstance(artwork_data, list):
                                    artwork = artwork_data[0]
                                else:
                                    artwork = artwork_data
                                break
                        except:
                            continue
                
                # M4A/MP4 tags
                elif 'covr' in tags:
                    try:
                        artwork = tags['covr'][0]
                    except:
                        pass
            
            if artwork:
                try:
                    # Handle different artwork formats
                    if hasattr(artwork, 'data'):
                        # mutagen APIC object
                        image_data = artwork.data
                    elif isinstance(artwork, bytes):
                        # Raw bytes
                        image_data = artwork
                    else:
                        # Try to get data attribute
                        image_data = getattr(artwork, 'data', artwork)
                    
                    # Create image from bytes
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Convert to RGB if necessary
                    if image.mode in ('RGBA', 'LA', 'P'):
                        image = image.convert('RGB')
                    
                    # Resize to reasonable thumbnail size (300x300)
                    image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                    
                    # Save thumbnail
                    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                    image.save(thumbnail_path, 'JPEG', quality=85)
                    
                    logger.info(f"Thumbnail extracted for {filename_stem}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"Failed to process thumbnail for {filename_stem}: {e}")
                    return False
            
            logger.info(f"No artwork found for {filename_stem}")
            return False
            
        except Exception as e:
            logger.error(f"Error extracting thumbnail from {file_path}: {e}")
            return False
    
    def get_thumbnail_base64(self, file_path):
        """Get base64 encoded thumbnail data"""
        try:
            filename_stem = Path(file_path).stem
            thumbnail_path = Path(CONFIG['thumbnails_dir']) / f"{filename_stem}.jpg"
            
            if thumbnail_path.exists():
                import base64
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_data = f.read()
                    return base64.b64encode(thumbnail_data).decode('utf-8')
            
            return None
        except Exception as e:
            logger.error(f"Error getting base64 thumbnail for {file_path}: {e}")
            return None
    
    def find_duplicates(self, file_path, metadata):
        """Find duplicate files in the catalog"""
        duplicates = []
        file_hash = metadata.get('file_hash')
        
        if not file_hash:
            return duplicates
        
        for song in self.catalog['songs']:
            if song.get('file_hash') == file_hash:
                duplicates.append(song)
        
        return duplicates
    
    def check_duplicates_in_library(self):
        """Check for duplicates in the library based on name and format rules"""
        try:
            library_path = Path(CONFIG['library_path'])
            duplicate_groups = []
            moved_files = []
            failed_moves = []
            
            # Get all music files in library
            music_files = []
            for file_path in library_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in CONFIG['supported_formats']:
                    music_files.append(file_path)
            
            # Group files by normalized name (case-insensitive, without extension)
            name_groups = {}
            for file_path in music_files:
                # Get filename without extension
                filename_stem = file_path.stem
                # Normalize to lowercase for comparison
                normalized_name = filename_stem.lower()
                
                if normalized_name not in name_groups:
                    name_groups[normalized_name] = []
                name_groups[normalized_name].append(file_path)
            
            # Find groups with multiple files (potential duplicates)
            for normalized_name, files in name_groups.items():
                if len(files) > 1:
                    # This is a potential duplicate group
                    duplicate_group = {
                        'normalized_name': normalized_name,
                        'files': files,
                        'formats': [f.suffix.lower() for f in files],
                        'moved_files': []
                    }
                    
                    # Check if files have different formats or different case
                    formats = set(f.suffix.lower() for f in files)
                    names = set(f.stem for f in files)
                    
                    # Rule 1: Same name but different format
                    # Rule 2: Same name but different uppercase and lowercase
                    if len(formats) > 1 or len(names) > 1:
                        # These are duplicates according to our rules
                        duplicate_groups.append(duplicate_group)
                        
                        # Move ALL files in the duplicate group to duplicate folder
                        for file_path in files:
                            try:
                                # Create duplicate folder path
                                duplicate_path = Path(CONFIG['duplicate_path']) / file_path.name
                                
                                # Handle filename conflicts in duplicate folder
                                counter = 1
                                original_duplicate_path = duplicate_path
                                while duplicate_path.exists():
                                    name_parts = original_duplicate_path.stem, f"({counter})", original_duplicate_path.suffix
                                    duplicate_path = original_duplicate_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                                    counter += 1
                                
                                # Move file to duplicate folder
                                shutil.move(str(file_path), str(duplicate_path))
                                moved_files.append({
                                    'original_path': str(file_path),
                                    'duplicate_path': str(duplicate_path),
                                    'reason': f"Part of duplicate group: {', '.join([f.name for f in files])}"
                                })
                                
                                # Remove from catalog since it's now in duplicate folder
                                self.catalog['songs'] = [
                                    song for song in self.catalog['songs'] 
                                    if song.get('file_path') != str(file_path)
                                ]
                                
                                duplicate_group['moved_files'].append(str(duplicate_path))
                                logger.info(f"Moved file from duplicate group to duplicate folder: {file_path.name} -> {duplicate_path.name}")
                                
                            except Exception as e:
                                failed_moves.append({
                                    'file_path': str(file_path),
                                    'error': str(e)
                                })
                                logger.error(f"Failed to move duplicate {file_path.name}: {e}")
            
            # Save updated catalog
            if moved_files:
                self.save_catalog()
                logger.info(f"Duplicate check completed: {len(moved_files)} files from duplicate groups moved to duplicate folder")
            
            return {
                'success': True,
                'duplicate_groups': len(duplicate_groups),
                'moved_files': len(moved_files),
                'failed_moves': len(failed_moves),
                'moved_file_details': moved_files,
                'failed_move_details': failed_moves,
                'total_files_checked': len(music_files)
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_music_file(self, file_path):
        """Add a music file to the library"""
        try:
            # Extract metadata
            metadata = self.extract_metadata(file_path)
            
            # Validate that essential metadata was extracted
            if not metadata or not metadata.get('title'):
                raise Exception("Failed to extract essential metadata")
            
            # Check for duplicates by comparing with existing files in library
            # First, check by file hash (exact duplicates)
            file_hash = metadata.get('file_hash')
            exact_duplicates = []
            if file_hash:
                for song in self.catalog['songs']:
                    if song.get('file_hash') == file_hash:
                        exact_duplicates.append(song)
            
            # Also check for name-based duplicates (same name, different format/case)
            filename_stem = Path(file_path).stem
            normalized_name = filename_stem.lower()
            name_duplicates = []
            
            for song in self.catalog['songs']:
                song_path = Path(song.get('file_path', ''))
                if song_path.exists():
                    song_stem = song_path.stem
                    song_normalized = song_stem.lower()
                    if song_normalized == normalized_name:
                        name_duplicates.append(song)
            
            # Combine all duplicates
            all_duplicates = exact_duplicates + name_duplicates
            
            if all_duplicates:
                # Move to duplicate folder
                duplicate_path = Path(CONFIG['duplicate_path']) / Path(file_path).name
                
                # Handle filename conflicts in duplicate folder
                counter = 1
                original_duplicate_path = duplicate_path
                while duplicate_path.exists():
                    name_parts = original_duplicate_path.stem, f"({counter})", original_duplicate_path.suffix
                    duplicate_path = original_duplicate_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                    counter += 1
                
                shutil.move(file_path, duplicate_path)
                metadata['file_path'] = str(duplicate_path)
                metadata['status'] = 'duplicate'
                logger.info(f"Duplicate found during add: {file_path} -> {duplicate_path}")
                
                return {
                    'success': True,
                    'metadata': metadata,
                    'duplicates': all_duplicates,
                    'status': 'duplicate',
                    'moved_to_duplicate': str(duplicate_path)
                }
            else:
                # Move to library
                library_path = Path(CONFIG['library_path']) / Path(file_path).name
                shutil.move(file_path, library_path)
                metadata['file_path'] = str(library_path)
                metadata['status'] = 'library'
                metadata['date_added'] = datetime.now().isoformat()
                
                # Add to catalog
                self.catalog['songs'].append(metadata)
                self.save_catalog()
                logger.info(f"Added to library: {file_path} - Catalog updated and saved")
                
                return {
                    'success': True,
                    'metadata': metadata,
                    'duplicates': [],
                    'status': 'library'
                }
            
        except Exception as e:
            # File processing failed - move to trash
            logger.error(f"Error processing music file {file_path}: {e}")
            try:
                trash_path = Path(CONFIG['trash_path']) / Path(file_path).name
                
                # Handle filename conflicts in trash
                counter = 1
                original_trash_path = trash_path
                while trash_path.exists():
                    name_parts = original_trash_path.stem, f"({counter})", original_trash_path.suffix
                    trash_path = original_trash_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                    counter += 1
                
                shutil.move(str(file_path), str(trash_path))
                logger.warning(f"Failed to process {Path(file_path).name}: {e}. Moved to trash: {trash_path.name}")
                
                return {
                    'success': False,
                    'error': str(e),
                    'moved_to_trash': str(trash_path),
                    'status': 'trash'
                }
                
            except Exception as move_error:
                logger.error(f"Failed to move corrupted file {Path(file_path).name} to trash: {move_error}")
                return {
                    'success': False,
                    'error': f"Processing failed: {e}. Moving to trash also failed: {move_error}",
                    'status': 'failed'
                }
    
    def scan_library(self):
        """Scan the library directory and update catalog"""
        try:
            library_path = Path(CONFIG['library_path'])
            new_songs = []
            failed_files = []
            moved_to_trash = []
            updated_thumbnails = 0
            
            for file_path in library_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in CONFIG['supported_formats']:
                    # Check if already in catalog
                    existing_index = None
                    for i, song in enumerate(self.catalog['songs']):
                        if song.get('file_path') == str(file_path):
                            existing_index = i
                            break
                    
                    if existing_index is not None:
                        # Update existing entry with thumbnail info if missing
                        existing_song = self.catalog['songs'][existing_index]
                        if 'has_thumbnail' not in existing_song:
                            try:
                                audio = mutagen.File(file_path)
                                if audio:
                                    thumbnail_extracted = self.extract_thumbnail(file_path, audio)
                                    existing_song['has_thumbnail'] = thumbnail_extracted
                                    
                                    # Add base64 thumbnail data if available
                                    if thumbnail_extracted:
                                        thumbnail_base64 = self.get_thumbnail_base64(file_path)
                                        if thumbnail_base64:
                                            existing_song['thumbnail_base64'] = thumbnail_base64
                                    
                                    updated_thumbnails += 1
                                    logger.info(f"Updated thumbnail info for existing file: {file_path.name}")
                            except Exception as e:
                                logger.warning(f"Failed to update thumbnail info for {file_path.name}: {e}")
                                existing_song['has_thumbnail'] = False
                    else:
                        # New file
                        try:
                            # Try to extract metadata
                            metadata = self.extract_metadata(file_path)
                            
                            # Validate that essential metadata was extracted
                            if not metadata or not metadata.get('title'):
                                raise Exception("Failed to extract essential metadata")
                            
                            metadata['date_added'] = datetime.now().isoformat()
                            metadata['status'] = 'library'
                            new_songs.append(metadata)
                            logger.info(f"Successfully processed: {file_path.name}")
                            
                        except Exception as e:
                            # File processing failed - move to trash
                            failed_files.append(str(file_path))
                            try:
                                trash_path = Path(CONFIG['trash_path']) / file_path.name
                                
                                # Handle filename conflicts in trash
                                counter = 1
                                original_trash_path = trash_path
                                while trash_path.exists():
                                    name_parts = original_trash_path.stem, f"({counter})", original_trash_path.suffix
                                    trash_path = original_trash_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                                    counter += 1
                                
                                shutil.move(str(file_path), str(trash_path))
                                moved_to_trash.append(str(trash_path))
                                logger.warning(f"Failed to process {file_path.name}: {e}. Moved to trash: {trash_path.name}")
                                
                            except Exception as move_error:
                                logger.error(f"Failed to move corrupted file {file_path.name} to trash: {move_error}")
                                failed_files.append(str(file_path))
            
            # Add new songs to catalog
            self.catalog['songs'].extend(new_songs)
            self.save_catalog()
            
            # Log summary
            logger.info(f"Library scan completed: {len(new_songs)} new songs found, {updated_thumbnails} thumbnail info updated, {len(self.catalog['songs'])} total songs - Catalog saved")
            if moved_to_trash:
                logger.warning(f"Moved {len(moved_to_trash)} failed files to trash: {', '.join([Path(p).name for p in moved_to_trash])}")
            
            return {
                'success': True,
                'new_songs': len(new_songs),
                'updated_thumbnails': updated_thumbnails,
                'total_songs': len(self.catalog['songs']),
                'failed_files': len(failed_files),
                'moved_to_trash': len(moved_to_trash),
                'failed_file_names': [Path(f).name for f in failed_files]
            }
            
        except Exception as e:
            logger.error(f"Error scanning library: {e}")
            return {'success': False, 'error': str(e)}
    

    
    def get_statistics(self):
        """Get library statistics"""
        total_songs = len(self.catalog['songs'])
        total_size = sum(song.get('file_size', 0) for song in self.catalog['songs'])
        
        # Count by format
        formats = {}
        for song in self.catalog['songs']:
            ext = Path(song.get('file_path', '')).suffix.lower()
            formats[ext] = formats.get(ext, 0) + 1
        
        # Count by artist
        artists = {}
        for song in self.catalog['songs']:
            artist = song.get('artist', 'Unknown Artist')
            artists[artist] = artists.get(artist, 0) + 1
        
        return {
            'total_songs': total_songs,
            'total_size': total_size,
            'formats': formats,
            'artists': artists,
            'last_updated': self.catalog.get('last_updated')
        }
    
    def search_songs(self, query):
        """Search songs in the catalog"""
        query = query.lower()
        results = []
        
        for song in self.catalog['songs']:
            title = song.get('title', '').lower()
            artist = song.get('artist', '').lower()
            album = song.get('album', '').lower()
            
            if query in title or query in artist or query in album:
                results.append(song)
        
        return results
    
    def export_catalog_backup(self):
        """Export catalog to a timestamped backup file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'mayi-music-list-backup-{timestamp}.json'
            backup_path = Path(backup_filename)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Catalog backup exported to: {backup_path} in current directory")
            return {'success': True, 'backup_file': str(backup_path)}
        except Exception as e:
            logger.error(f"Error exporting catalog backup: {e}")
            return {'success': False, 'error': str(e)}

# Initialize the manager
manager = MusicLibraryManager()

# Web routes
@app.route('/')
def index():
    """Main interface"""
    stats = manager.get_statistics()
    return render_template('index.html', stats=stats)

@app.route('/api/songs')
def get_songs():
    """Get all songs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    
    songs = manager.catalog['songs']
    
    if search:
        songs = manager.search_songs(search)
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_songs = songs[start:end]
    
    return jsonify({
        'songs': paginated_songs,
        'total': len(songs),
        'page': page,
        'per_page': per_page,
        'pages': (len(songs) + per_page - 1) // per_page
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and process music files"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    # Save to new folder temporarily
    temp_path = Path(CONFIG['new_path']) / file.filename
    file.save(temp_path)
    
    # Process the file
    result = manager.add_music_file(str(temp_path))
    return jsonify(result)

@app.route('/api/scan', methods=['POST'])
def scan_library():
    """Scan the library"""
    result = manager.scan_library()
    return jsonify(result)

@app.route('/api/check-duplicates', methods=['POST'])
def check_duplicates():
    """Check for duplicates in the library"""
    result = manager.check_duplicates_in_library()
    return jsonify(result)



@app.route('/api/statistics')
def get_statistics():
    """Get library statistics"""
    stats = manager.get_statistics()
    return jsonify(stats)

@app.route('/api/search')
def search():
    """Search songs"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'results': []})
    
    results = manager.search_songs(query)
    # Convert to the format expected by index.html
    music_files = []
    for song in results:
        # Format duration
        duration = song.get('duration', 0)
        duration_formatted = f"{duration // 60}:{duration % 60:02d}" if duration else ""
        
        # Format bitrate
        bitrate = song.get('bitrate', 0)
        bitrate_formatted = f"{bitrate // 1000}kbps" if bitrate else ""
        
        # Format file size
        size = song.get('file_size', 0)
        if size < 1024:
            size_formatted = f"{size} B"
        elif size < 1024 * 1024:
            size_formatted = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_formatted = f"{size / (1024 * 1024):.1f} MB"
        else:
            size_formatted = f"{size / (1024 * 1024 * 1024):.1f} GB"
        
        # Get format from file path
        file_path = song.get('file_path', '')
        format_ext = Path(file_path).suffix.upper().replace('.', '') if file_path else ""
        
        # Get filename from file path
        filename = Path(file_path).name if file_path else ""
        
        music_file = {
            'filename': filename,
            'title': song.get('title', ''),
            'artist': song.get('artist', ''),
            'album': song.get('album', ''),
            'duration': duration,
            'duration_formatted': duration_formatted,
            'bitrate': bitrate,
            'bitrate_formatted': bitrate_formatted,
            'format': format_ext,
            'size': size,
            'size_formatted': size_formatted,
            'has_thumbnail': song.get('has_thumbnail', False)
        }
        music_files.append(music_file)
    
    return jsonify({'results': music_files})

@app.route('/api/serve/<path:filename>')
def serve_file(filename):
    """Serve music files"""
    file_path = Path(CONFIG['library_path']) / filename
    if file_path.exists():
        return send_file(file_path)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/library')
def get_library():
    """Get all music files in library format"""
    music_files = []
    for song in manager.catalog['songs']:
        # Format duration
        duration = song.get('duration', 0)
        duration_formatted = f"{duration // 60}:{duration % 60:02d}" if duration else ""
        
        # Format bitrate
        bitrate = song.get('bitrate', 0)
        bitrate_formatted = f"{bitrate // 1000}kbps" if bitrate else ""
        
        # Format file size
        size = song.get('file_size', 0)
        if size < 1024:
            size_formatted = f"{size} B"
        elif size < 1024 * 1024:
            size_formatted = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_formatted = f"{size / (1024 * 1024):.1f} MB"
        else:
            size_formatted = f"{size / (1024 * 1024 * 1024):.1f} GB"
        
        # Get format from file path
        file_path = song.get('file_path', '')
        format_ext = Path(file_path).suffix.upper().replace('.', '') if file_path else ""
        
        # Get filename from file path
        filename = Path(file_path).name if file_path else ""
        
        music_file = {
            'filename': filename,
            'title': song.get('title', ''),
            'artist': song.get('artist', ''),
            'album': song.get('album', ''),
            'duration': duration,
            'duration_formatted': duration_formatted,
            'bitrate': bitrate,
            'bitrate_formatted': bitrate_formatted,
            'format': format_ext,
            'size': size,
            'size_formatted': size_formatted,
            'has_thumbnail': song.get('has_thumbnail', False)
        }
        
        # Add base64 thumbnail if available
        if song.get('has_thumbnail', False) and 'thumbnail_base64' not in song:
            thumbnail_base64 = manager.get_thumbnail_base64(song.get('file_path', ''))
            if thumbnail_base64:
                music_file['thumbnail_base64'] = thumbnail_base64
        elif 'thumbnail_base64' in song:
            music_file['thumbnail_base64'] = song['thumbnail_base64']
        
        music_files.append(music_file)
    
    return jsonify({
        'music_files': music_files,
        'total_files': len(music_files)
    })

@app.route('/api/library/stats')
def get_library_stats():
    """Get library statistics in the format expected by index.html"""
    stats = manager.get_statistics()
    
    # Calculate total size
    total_size = sum(song.get('file_size', 0) for song in manager.catalog['songs'])
    
    # Format total size
    if total_size < 1024:
        total_size_formatted = f"{total_size} B"
    elif total_size < 1024 * 1024:
        total_size_formatted = f"{total_size / 1024:.1f} KB"
    elif total_size < 1024 * 1024 * 1024:
        total_size_formatted = f"{total_size / (1024 * 1024):.1f} MB"
    else:
        total_size_formatted = f"{total_size / (1024 * 1024 * 1024):.1f} GB"
    
    # Count files with thumbnails
    files_with_thumbnails = sum(1 for song in manager.catalog['songs'] if song.get('has_thumbnail', False))
    
    return jsonify({
        'total_files': len(manager.catalog['songs']),
        'total_size_formatted': total_size_formatted,
        'files_with_thumbnails': files_with_thumbnails,
        'export_date': stats.get('last_updated', datetime.now().isoformat())
    })

@app.route('/api/library/add')
def add_music():
    """Add music files from New directory"""
    try:
        new_files = list(Path(CONFIG['new_path']).glob('*'))
        music_files = [f for f in new_files if f.suffix.lower() in CONFIG['supported_formats']]
        
        if not music_files:
            return jsonify({'success': False, 'error': 'No music files found in New directory'})
        
        added_count = 0
        moved_to_trash = []
        moved_to_duplicates = []
        failed_files = []
        
        for file_path in music_files:
            result = manager.add_music_file(str(file_path))
            if result.get('success'):
                if result.get('status') == 'library':
                    added_count += 1
                elif result.get('status') == 'duplicate':
                    moved_to_duplicates.append(Path(file_path).name)
            else:
                if result.get('status') == 'trash':
                    moved_to_trash.append(Path(file_path).name)
                else:
                    failed_files.append(Path(file_path).name)
        
        # Build response message
        message_parts = []
        if added_count > 0:
            message_parts.append(f"Added {added_count} files to library")
        if moved_to_duplicates:
            message_parts.append(f"Moved {len(moved_to_duplicates)} duplicates to Duplicate folder")
        if moved_to_trash:
            message_parts.append(f"Moved {len(moved_to_trash)} failed files to Trash folder")
        if failed_files:
            message_parts.append(f"Failed to process {len(failed_files)} files")
        
        message = "; ".join(message_parts) if message_parts else "No files processed"
        
        return jsonify({
            'success': True,
            'message': message,
            'added_count': added_count,
            'moved_to_duplicates': len(moved_to_duplicates),
            'moved_to_trash': len(moved_to_trash),
            'failed_count': len(failed_files),
            'duplicate_files': moved_to_duplicates,
            'trash_files': moved_to_trash,
            'failed_files': failed_files
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/library/scan')
def scan_library_endpoint():
    """Scan library directory for new files"""
    try:
        result = manager.scan_library()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/thumbnail/<path:filename>')
def get_thumbnail(filename):
    """Serve thumbnail images"""
    try:
        # Decode the filename from URL encoding
        decoded_filename = unquote(filename)
        thumbnail_path = Path(CONFIG['thumbnails_dir']) / f"{Path(decoded_filename).stem}.jpg"
        
        if thumbnail_path.exists():
            return send_file(thumbnail_path, mimetype='image/jpeg')
        else:
            # Return a default image or 404
            logger.warning(f"Thumbnail not found: {thumbnail_path}")
            return jsonify({'error': 'Thumbnail not found'}), 404
    except Exception as e:
        logger.error(f"Error serving thumbnail for {filename}: {e}")
        return jsonify({'error': 'Thumbnail error'}), 500

@app.route('/api/play/<path:filename>')
def play_audio(filename):
    """Serve audio files for playback"""
    try:
        # Decode the filename from URL encoding
        decoded_filename = unquote(filename)
        audio_path = Path(CONFIG['library_path']) / decoded_filename
        
        if audio_path.exists():
            # Determine MIME type based on file extension
            mime_type = 'audio/mpeg'  # Default for MP3
            if audio_path.suffix.lower() == '.flac':
                mime_type = 'audio/flac'
            elif audio_path.suffix.lower() == '.m4a':
                mime_type = 'audio/mp4'
            elif audio_path.suffix.lower() == '.wav':
                mime_type = 'audio/wav'
            elif audio_path.suffix.lower() == '.ogg':
                mime_type = 'audio/ogg'
            
            return send_file(audio_path, mimetype=mime_type)
        else:
            logger.warning(f"Audio file not found: {audio_path}")
            return jsonify({'error': 'Audio file not found'}), 404
    except Exception as e:
        logger.error(f"Error serving audio for {filename}: {e}")
        return jsonify({'error': 'Audio error'}), 500



@app.route('/api/export-backup', methods=['POST'])
def export_backup():
    """Export catalog to backup file"""
    try:
        result = manager.export_catalog_backup()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🎵 Unified Music Library Management System")
    print("==========================================")
    print(f"📁 Library: {CONFIG['library_path']}")
    print(f"🆕 New files: {CONFIG['new_path']}")
    print(f"🔄 Duplicates: {CONFIG['duplicate_path']}")
    print(f"🗑️  Trash: {CONFIG['trash_path']}")
    print(f"📝 Log file: {CONFIG['log_file']}")
    print(f"💾 Catalog: {CONFIG['json_file']}")
    print()
    print("🌐 Starting web interface...")
    print("📱 Open your browser to: http://localhost:8088")
    print("⏹️  Press Ctrl+C to stop")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=8088)
