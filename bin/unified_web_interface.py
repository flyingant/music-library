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
import struct
import base64
import tempfile
import platform
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import quote, unquote
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
    from flask_cors import CORS
    import mutagen
    from PIL import Image
    import io
    
    # Import decryptor functionality (optional - only if decryptor is available)
    decryptor_available = False
    try:
        import cryptography
        import requests
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        decryptor_available = True
        print("🔓 Music decryption dependencies available")
    except ImportError:
        print("⚠️  Decryptor dependencies not available. Music decryption features will be disabled.")
        print("💡 To enable decryption, install: pip install cryptography requests")
    
    # Try to import mutagen for audio metadata handling
    try:
        from mutagen.flac import FLAC, Picture
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, APIC
        MUTAGEN_AVAILABLE = True
    except ImportError:
        MUTAGEN_AVAILABLE = False
        print("⚠️  mutagen library not available. Install with: pip install mutagen")
        print("   Image embedding will be disabled.")
    
    # Try to import music-metadata for metadata parsing
    try:
        import music_metadata
        MUSIC_METADATA_AVAILABLE = True
    except ImportError:
        MUSIC_METADATA_AVAILABLE = False
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please run: pip install flask flask-cors mutagen pillow cryptography requests")
    sys.exit(1)

# Enhanced Music Decryptor Implementation
@dataclass
class DecryptResult:
    """Result of decryption operation"""
    title: str
    album: Optional[str] = None
    artist: Optional[str] = None
    mime: str = ""
    ext: str = ""
    file: str = ""
    data: bytes = b""
    picture: Optional[bytes] = None
    picture_url: Optional[str] = None
    raw_ext: str = ""
    raw_filename: str = ""
class QmcMask:
    """QMC mask implementation for QQ Music decryption"""
    
    # QMC constants
    QMC_DEFAULT_MASK_MATRIX = [
        0xde, 0x51, 0xfa, 0xc3, 0x4a, 0xd6, 0xca, 0x90,
        0x7e, 0x67, 0x5e, 0xf7, 0xd5, 0x52, 0x84, 0xd8,
        0x47, 0x95, 0xbb, 0xa1, 0xaa, 0xc6, 0x66, 0x23,
        0x92, 0x62, 0xf3, 0x74, 0xa1, 0x9f, 0xf4, 0xa0,
        0x1d, 0x3f, 0x5b, 0xf0, 0x13, 0x0e, 0x09, 0x3d,
        0xf9, 0xbc, 0x00, 0x11
    ]
    
    def __init__(self, matrix: Optional[List[int]] = None):
        """Initialize QMC mask with matrix"""
        if matrix is None:
            matrix = self.QMC_DEFAULT_MASK_MATRIX
        
        if len(matrix) == 44:
            self.matrix_128 = self._generate_128(matrix)
        elif len(matrix) == 128:
            self.matrix_128 = matrix
        else:
            raise ValueError("Invalid mask length")
    
    def _generate_128(self, matrix_44: List[int]) -> List[int]:
        """Generate 128-byte matrix from 44-byte matrix"""
        matrix_128 = [0] * 128
        for i in range(128):
            matrix_128[i] = matrix_44[i % 44]
        return matrix_128
    
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data using the mask"""
        result = bytearray(data)
        for cur in range(len(data)):
            result[cur] ^= self.matrix_128[cur & 0x7f]
        return bytes(result)
    
    def get_default(self):
        """Get default mask"""
        return self


class ImageProcessor:
    """Enhanced image processing capabilities matching TypeScript implementation"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def download_and_process_image(self, image_url: str) -> Optional[Dict[str, Any]]:
        """Download and process image with proper error handling"""
        try:
            # Convert HTTP to HTTPS and add size parameters (matching TypeScript)
            if image_url.startswith('http://'):
                image_url = image_url.replace('http://', 'https://')
            
            if '?' not in image_url:
                image_url += '?param=500y500'
            
            if self.verbose:
                print(f"🖼️  Downloading artwork from: {image_url}")
            
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                if self.verbose:
                    print(f"⚠️  Invalid content type: {content_type}")
                return None
            
            image_data = response.content
            
            if self.verbose:
                print(f"✅ Downloaded artwork: {len(image_data)} bytes")
            
            # Resize large images (>16MB) - matching TypeScript behavior
            if len(image_data) >= 1 << 24:  # 16MB
                if self.verbose:
                    print(f"🔄 Resizing large image ({len(image_data)} bytes)")
                
                img = Image.open(io.BytesIO(image_data))
                
                # Resize to half height while maintaining aspect ratio
                new_height = img.height // 2
                new_width = int(img.width * (new_height / img.height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to JPEG
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85)
                image_data = output.getvalue()
                
                if self.verbose:
                    print(f"🔄 Resized image to {len(image_data)} bytes")
            
            return {
                'buffer': image_data,
                'mime': content_type,
                'url': image_url
            }
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Failed to download/process artwork: {e}")
            return None
    
    def query_cover_image(self, title: str, artist: Optional[str] = None, album: Optional[str] = None) -> Optional[str]:
        """Query external API for cover image (matching TypeScript implementation)"""
        try:
            api_endpoint = "https://um-api.ixarea.com/music/qq-cover"
            params = {
                "Title": title,
                "Artist": artist or "",
                "Album": album or ""
            }
            
            if self.verbose:
                print(f"🔍 Querying cover image API for: {title} - {artist}")
            
            response = requests.get(api_endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("Id") and data.get("Type"):
                cover_url = f"https://stats.ixarea.com/apis/music/qq-cover/{data['Type']}/{data['Id']}"
                if self.verbose:
                    print(f"✅ Found cover image: {cover_url}")
                return cover_url
            
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Failed to query cover image: {e}")
            return None


class AudioMetadataHandler:
    """Handle audio metadata embedding (matching TypeScript implementation)"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def embed_artwork_to_flac(self, audio_data: bytes, cover_data: bytes) -> bytes:
        """Embed artwork into FLAC file (matching TypeScript MetaFlac implementation)"""
        if not MUTAGEN_AVAILABLE:
            if self.verbose:
                print("⚠️  mutagen library not available for FLAC artwork embedding")
            return audio_data
        
        try:
            # Create a temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # Load FLAC file
                audio = FLAC(temp_file.name)
                
                # Create picture metadata
                picture = Picture()
                picture.type = 3  # Front cover
                picture.mime = 'image/jpeg'
                picture.desc = 'Cover'
                picture.data = cover_data
                
                # Add picture to metadata
                audio.add_picture(picture)
                audio.save()
                
                # Read back the modified file
                with open(temp_file.name, 'rb') as f:
                    result = f.read()
                
                # Clean up
                os.unlink(temp_file.name)
                
                if self.verbose:
                    print(f"✅ Embedded artwork into FLAC file")
                
                return result
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Failed to embed FLAC artwork: {e}")
            return audio_data
    
    def embed_artwork_to_mp3(self, audio_data: bytes, cover_data: bytes) -> bytes:
        """Embed artwork into MP3 file (matching TypeScript ID3Writer implementation)"""
        if not MUTAGEN_AVAILABLE:
            if self.verbose:
                print("⚠️  mutagen library not available for MP3 artwork embedding")
            return audio_data
        
        try:
            # Create a temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # Load MP3 file
                audio = MP3(temp_file.name, ID3=ID3)
                
                # Ensure ID3 tag exists
                if audio.tags is None:
                    audio.tags = ID3()
                
                # Add artwork
                audio.tags.add(APIC(
                    encoding=3,  # UTF-8
                    mime='image/jpeg',
                    type=3,  # Front cover
                    desc='Cover',
                    data=cover_data
                ))
                
                audio.save()
                
                # Read back the modified file
                with open(temp_file.name, 'rb') as f:
                    result = f.read()
                
                # Clean up
                os.unlink(temp_file.name)
                
                if self.verbose:
                    print(f"✅ Embedded artwork into MP3 file")
                
                return result
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Failed to embed MP3 artwork: {e}")
            return audio_data


class EnhancedUniversalDecryptor:
    """Enhanced universal decryptor with complete image handling capabilities"""
    
    FORMAT_HANDLERS = {
        # Netease Cloud Music
        "ncm": "decrypt_ncm",
        "uc": "decrypt_ncm_cache",
        
        # QQ Music
        "qmc0": "decrypt_qmc",
        "qmc3": "decrypt_qmc", 
        "qmc2": "decrypt_qmc",
        "qmcogg": "decrypt_qmc",
        "qmcflac": "decrypt_qmc",
        "bkcmp3": "decrypt_qmc",
        "bkcflac": "decrypt_qmc",
        "mgg": "decrypt_qmc",
        "mflac": "decrypt_qmc",
        "6d7033": "decrypt_qmc",
        "6f6767": "decrypt_qmc",
        "666c6163": "decrypt_qmc",
        "tkm": "decrypt_qmc",
        "6d3461": "decrypt_qmc",
        "776176": "decrypt_qmc",
        
        # KuGou Music
        "kgm": "decrypt_kgm",
        "kgma": "decrypt_kgm",
        "vpr": "decrypt_kgm",
        
        # KuWo Music
        "kwm": "decrypt_kwm",
        
        # Xiami Music and Raw formats
        "xm": "decrypt_xm",
        "wav": "decrypt_raw",
        "mp3": "decrypt_raw", 
        "flac": "decrypt_raw",
        "m4a": "decrypt_raw",
        "ogg": "decrypt_raw",
    }
    
    def __init__(self, verbose: bool = False):
        """Initialize the enhanced universal decryptor"""
        self.verbose = verbose
        self.image_processor = ImageProcessor(verbose)
        self.metadata_handler = AudioMetadataHandler(verbose)
    
    def decrypt_file(self, file_path: str, output_dir: Optional[str] = None) -> DecryptResult:
        """Main method to decrypt any supported file format with enhanced image handling"""
        if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
        # Extract file extension
        file_ext = self._get_file_extension(file_path)
        
        if file_ext not in self.FORMAT_HANDLERS:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Get the appropriate handler method
        handler_name = self.FORMAT_HANDLERS[file_ext]
        handler_method = getattr(self, handler_name)
        
        # Decrypt the file
        result = handler_method(file_path, file_ext)
        
        # Save the decrypted file
        if output_dir is None:
            output_dir = os.path.dirname(file_path)
        
        output_path = os.path.join(output_dir, result.file)
        with open(output_path, 'wb') as f:
            f.write(result.data)
        
        # Display metadata
        self._display_metadata(result, output_path)
        
        return result
    
    def _get_file_extension(self, file_path: str) -> str:
        """Extract file extension"""
        return Path(file_path).suffix[1:].lower()
    
    def _split_filename(self, filename: str) -> Dict[str, str]:
        """Split filename into name and extension"""
        path = Path(filename)
        return {
            'name': path.stem,
            'ext': path.suffix[1:].lower()
        }
    
    def _sniff_audio_ext(self, data: bytes, fallback_ext: str = "mp3") -> str:
        """Detect audio format from data"""
        headers = {
            b'ID3': 'mp3',
            b'fLaC': 'flac', 
            b'OggS': 'ogg',
            b'ftyp': 'm4a',
            b'RIFF': 'wav'
        }
        
        for header, ext in headers.items():
            if data.startswith(header):
                return ext
            if len(data) > 4 and data[4:4+len(header)] == header:
                return ext
        
        return fallback_ext
    
    def _get_mime_type(self, ext: str) -> str:
        """Get MIME type for audio extension"""
        mime_types = {
            'mp3': 'audio/mpeg',
            'flac': 'audio/flac',
            'm4a': 'audio/mp4', 
            'ogg': 'audio/ogg',
            'wav': 'audio/x-wav'
        }
        return mime_types.get(ext, 'audio/mpeg')
    
    def _get_meta_from_filename(self, filename: str, exist_title: Optional[str] = None,
                               exist_artist: Optional[str] = None, separator: str = "-") -> Dict[str, str]:
        """Extract metadata from filename"""
        meta = {'title': exist_title or '', 'artist': exist_artist}
        
        items = filename.split(separator)
        if len(items) > 1:
            if not meta['artist']:
                meta['artist'] = items[0].strip()
            if not meta['title']:
                meta['title'] = items[1].strip()
        elif len(items) == 1:
            if not meta['title']:
                meta['title'] = items[0].strip()
        
        return meta
    
    def _display_metadata(self, result: DecryptResult, output_path: str):
        """Display comprehensive metadata"""
        if self.verbose:
            print(f"🎵 Decrypted: {result.file}")
            print(f"📁 Saved to: {output_path}")
            print(f"📊 File size: {len(result.data):,} bytes ({len(result.data)/1024/1024:.1f} MB)")
            print(f"🎼 Format: {result.ext.upper()} ({result.mime})")
            print(f"📝 Title: {result.title}")
            if result.artist:
                print(f"👤 Artist: {result.artist}")
            if result.album:
                print(f"💿 Album: {result.album}")
            if result.picture:
                print(f"🖼️  Cover: {len(result.picture):,} bytes (embedded)")
            elif result.picture_url:
                print(f"🖼️  Cover: {result.picture_url}")
            else:
                print(f"🖼️  Cover: None")
    
    # NCM (Netease Cloud Music) Decryptor with Enhanced Image Handling
    def decrypt_ncm(self, file_path: str, file_ext: str) -> DecryptResult:
        """Decrypt NCM files with complete image handling"""
        filename = self._split_filename(file_path)['name']
        
        # NCM constants
        CORE_KEY = bytes.fromhex("687a4852416d736f356b496e62617857")
        META_KEY = bytes.fromhex("2331346C6A6B5F215C5D2630553C2728")
        MAGIC_HEADER = bytes([0x43, 0x54, 0x45, 0x4E, 0x46, 0x44, 0x41, 0x4D])
        
        # Read file data
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        # Check magic header
        if not raw_data.startswith(MAGIC_HEADER):
            raise ValueError("Invalid NCM file: missing magic header")
        
        offset = 10  # Skip magic header and 2 bytes
        
        # Get key data
        def get_key_data():
            nonlocal offset
            key_len = struct.unpack('<I', raw_data[offset:offset+4])[0]
            offset += 4
            
            cipher_text = bytes(b ^ 0x64 for b in raw_data[offset:offset+key_len])
            offset += key_len
            
            # Decrypt with AES-ECB
            cipher = Cipher(algorithms.AES(CORE_KEY), modes.ECB(), backend=default_backend())
            decryptor = cipher.decryptor()
            unpadder = padding.PKCS7(128).unpadder()
            
            plain_text = decryptor.update(cipher_text) + decryptor.finalize()
            plain_text = unpadder.update(plain_text) + unpadder.finalize()
            
            return plain_text[17:]  # Skip first 17 bytes
        
        # Get key box
        def get_key_box():
            key_data = get_key_data()
            box = list(range(256))
            
            key_data_len = len(key_data)
            j = 0
            
            for i in range(256):
                j = (box[i] + j + key_data[i % key_data_len]) & 0xff
                box[i], box[j] = box[j], box[i]
            
            result = []
            for i in range(256):
                i = (i + 1) & 0xff
                si = box[i]
                sj = box[(i + si) & 0xff]
                result.append(box[(si + sj) & 0xff])
            
            return result
        
        # Get metadata
        def get_meta_data():
            nonlocal offset
            meta_data_len = struct.unpack('<I', raw_data[offset:offset+4])[0]
            offset += 4
            
            if meta_data_len == 0:
                return {}
            
            cipher_text = bytes(b ^ 0x63 for b in raw_data[offset:offset+meta_data_len])
            offset += meta_data_len
            
            # Decrypt metadata
            cipher = Cipher(algorithms.AES(META_KEY), modes.ECB(), backend=default_backend())
            decryptor = cipher.decryptor()
            unpadder = padding.PKCS7(128).unpadder()
            
            # Skip first 22 bytes and decode base64
            base64_data = cipher_text[22:].decode('utf-8')
            encrypted_data = base64.b64decode(base64_data)
            
            plain_text = decryptor.update(encrypted_data) + decryptor.finalize()
            plain_text = unpadder.update(plain_text) + unpadder.finalize()
            plain_text = plain_text.decode('utf-8')
            
            # Parse JSON metadata
            label_index = plain_text.find(':')
            if plain_text[:label_index] == 'dj':
                meta_data = json.loads(plain_text[label_index+1:])['mainMusic']
            else:
                meta_data = json.loads(plain_text[label_index+1:])
            
            # Filter only known fields and fix album pic URL
            if 'albumPic' in meta_data and meta_data['albumPic']:
                meta_data['albumPic'] = meta_data['albumPic'].replace('http://', 'https://') + '?param=500y500'
            
            return meta_data
        
        # Get audio data
        def get_audio(key_box):
            nonlocal offset
            offset += struct.unpack('<I', raw_data[offset+5:offset+9])[0] + 13
            audio_data = bytearray(raw_data[offset:])
            
            for i in range(len(audio_data)):
                audio_data[i] ^= key_box[i & 0xff]
            
            return bytes(audio_data)
        
        # Decrypt file
        key_box = get_key_box()
        ori_meta = get_meta_data()
        audio_data = get_audio(key_box)
        
        # Download and embed artwork if available
        cover_data = None
        cover_url = None
        if ori_meta.get('albumPic'):
            image_info = self.image_processor.download_and_process_image(ori_meta['albumPic'])
            if image_info:
                cover_data = image_info['buffer']
                cover_url = image_info['url']
        
        # Detect format
        ext = self._sniff_audio_ext(audio_data)
        mime = self._get_mime_type(ext)
        
        # Build metadata
        info = self._get_meta_from_filename(filename, ori_meta.get('musicName'))
        
        # Build artists list
        artists = []
        if ori_meta.get('artist'):
            for arr in ori_meta['artist']:
                if isinstance(arr, list) and len(arr) > 0:
                    artists.append(str(arr[0]))
        
        if not artists and info.get('artist'):
            artists = [a.strip() for a in info['artist'].split(',') if a.strip()]
        
        # Embed artwork if available
        if cover_data:
            if ext == 'flac':
                audio_data = self.metadata_handler.embed_artwork_to_flac(audio_data, cover_data)
            elif ext == 'mp3':
                audio_data = self.metadata_handler.embed_artwork_to_mp3(audio_data, cover_data)
        
        return DecryptResult(
            title=info.get('title', ''),
            album=ori_meta.get('album'),
            artist=', '.join(artists) if artists else None,
            mime=mime,
            ext=ext,
            file=f"{filename}.{ext}",
            data=audio_data,
            picture=cover_data,
            picture_url=cover_url,
            raw_ext=file_ext,
            raw_filename=filename
        )
    
    # QMC (QQ Music) Decryptor with Enhanced Image Handling
    def decrypt_qmc(self, file_path: str, file_ext: str) -> DecryptResult:
        """Decrypt QMC files with enhanced image handling"""
        filename = self._split_filename(file_path)['name']
        
        # QMC format mapping
        qmc_formats = {
            'qmc0': 'mp3', 'qmc3': 'mp3', 'bkcmp3': 'mp3', '6d7033': 'mp3',
            'qmc2': 'ogg', 'qmcogg': 'ogg', 'mgg': 'ogg', '6f6767': 'ogg',
            'qmcflac': 'flac', 'bkcflac': 'flac', 'mflac': 'flac', '666c6163': 'flac',
            'tkm': 'm4a', '6d3461': 'm4a',
            '776176': 'wav'
        }
        
        expected_format = qmc_formats.get(file_ext, 'mp3')
        
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create QMC mask
        qmc_mask = QmcMask()
        
        # Handle different QMC formats
        if file_ext in ['mgg', 'mflac']:
            # These formats have embedded keys
            key_len = struct.unpack('<I', file_data[-4:])[0]
            key_pos = len(file_data) - 4 - key_len
            audio_data = file_data[:key_pos]
            key_data = file_data[key_pos:key_pos + key_len]
            
            # Try to detect mask from audio data
            if file_ext == 'mflac':
                # Simplified detection
                pass
            else:  # mgg
                # Simplified detection
                pass
            
            if not qmc_mask:
                raise NotImplementedError(f"Could not detect mask for {file_ext} format")
        else:
            # Use default mask for other formats
            audio_data = file_data
            qmc_mask = qmc_mask.get_default()
        
        # Decrypt audio data
        decrypted_data = qmc_mask.decrypt(audio_data)
        
        # Detect actual format
        ext = self._sniff_audio_ext(decrypted_data, expected_format)
        mime = self._get_mime_type(ext)
        
        # Extract metadata from filename
        info = self._get_meta_from_filename(filename)
        
        # Try to get cover image from external API
        cover_data = None
        cover_url = None
        if info.get('title'):
            cover_url = self.image_processor.query_cover_image(
                info['title'], 
                info.get('artist'), 
                None  # album info not available from filename
            )
            
            if cover_url:
                image_info = self.image_processor.download_and_process_image(cover_url)
                if image_info:
                    cover_data = image_info['buffer']
        
        # Embed artwork if available
        if cover_data:
            if ext == 'flac':
                decrypted_data = self.metadata_handler.embed_artwork_to_flac(decrypted_data, cover_data)
            elif ext == 'mp3':
                decrypted_data = self.metadata_handler.embed_artwork_to_mp3(decrypted_data, cover_data)
        
        return DecryptResult(
            title=info.get('title', ''),
            album=None,
            artist=info.get('artist'),
            mime=mime,
            ext=ext,
            file=f"{filename}.{ext}",
            data=decrypted_data,
            picture=cover_data,
            picture_url=cover_url,
            raw_ext=file_ext,
            raw_filename=filename
        )
    
    # Placeholder methods for other formats
    def decrypt_kgm(self, file_path: str, file_ext: str) -> DecryptResult:
        """Decrypt KGM files"""
        # Placeholder implementation
        raise NotImplementedError("KGM decryption not yet implemented")
    
    def decrypt_kwm(self, file_path: str, file_ext: str) -> DecryptResult:
        """Decrypt KWM files"""
        # Placeholder implementation
        raise NotImplementedError("KWM decryption not yet implemented")
    
    def decrypt_xm(self, file_path: str, file_ext: str) -> DecryptResult:
        """Decrypt XM files"""
        # Placeholder implementation
        raise NotImplementedError("XM decryption not yet implemented")
    
    def decrypt_raw(self, file_path: str, file_ext: str) -> DecryptResult:
        """Handle raw audio files"""
        filename = self._split_filename(file_path)['name']
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        ext = self._sniff_audio_ext(data, file_ext)
        mime = self._get_mime_type(ext)
        info = self._get_meta_from_filename(filename)
        
        return DecryptResult(
            title=info.get('title', ''),
            album=None,
            artist=info.get('artist'),
            mime=mime,
            ext=ext,
            file=f"{filename}.{ext}",
            data=data,
            raw_ext=file_ext,
            raw_filename=filename
        )
    
    def decrypt_ncm_cache(self, file_path: str, file_ext: str) -> DecryptResult:
        """Decrypt NCM cache files"""
        # Placeholder implementation
        raise NotImplementedError("NCM cache decryption not yet implemented")


# Legacy MusicDecryptor wrapper for backwards compatibility
class MusicDecryptor:
    """Universal music decryptor for various encrypted formats"""
    
    @staticmethod
    def detect_file_format(file_path):
        """Detect file format from extension"""
        ext = Path(file_path).suffix[1:].lower()
        supported_formats = {
            'ncm', 'qmc0', 'qmc3', 'qmcflac', 'qmcogg', 
            'mflac', 'mgg', 'bkcmp3', 'bkcflac', 'tkm', 'xm'
        }
        return ext if ext in supported_formats else "unknown"
    
    @staticmethod
    def decrypt_file(file_path, output_dir=None):
        """Decrypt music file using the enhanced decryptor"""
        try:
            input_path = Path(file_path)
            if not input_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if output_dir is None:
                output_dir = input_path.parent
            
            # Use the enhanced decryptor if available
            if decryptor_available:
                try:
                    decryptor = EnhancedUniversalDecryptor(verbose=False)
                    result = decryptor.decrypt_file(str(input_path), str(output_dir))
                    
                    # Convert the result to the expected format
                    return {
                        'success': True,
                        'file': result.file,
                        'ext': result.ext,
                        'data': result.data,
                        'title': result.title,
                        'artist': result.artist,
                        'album': result.album
                    }
                except Exception as e:
                    logger.error(f"Enhanced decryptor failed: {e}")
                    # Fall back to simplified decryptor
            
            # Fall back to simplified decryptor if enhanced decryptor is not available
            format_type = MusicDecryptor.detect_file_format(str(input_path))
            
            if format_type.startswith('qmc'):
                return MusicDecryptor._decrypt_qmc(input_path, output_dir)
            elif format_type == 'ncm':
                return MusicDecryptor._decrypt_ncm(input_path, output_dir)
            else:
                # For unsupported formats, try to detect and copy
                return MusicDecryptor._handle_unknown_format(input_path, output_dir)
                
        except Exception as e:
            logger.error(f"Error in decrypt: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _decrypt_qmc(file_path, output_dir):
        """Decrypt QMC format files"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Simple QMC decryption using mask
            mask = QmcMask()
            decrypted_data = mask.decrypt(data)
            
            # Detect format from decrypted content
            format_ext = MusicDecryptor._detect_audio_format_from_data(decrypted_data)
            
            # Create output filename
            base_name = file_path.stem
            output_filename = f"{base_name}{format_ext}"
            output_path = Path(output_dir) / output_filename
            
            # Handle filename conflicts
            counter = 1
            original_output_path = output_path
            while output_path.exists():
                name_parts = original_output_path.stem, f"({counter})", original_output_path.suffix
                output_path = original_output_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                counter += 1
            
            # Write decrypted data
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            logger.info(f"Successfully decrypted QMC file: {file_path.name} -> {output_path.name}")
            
            return {
                'success': True,
                'file': str(output_path),
                'ext': output_path.suffix[1:],
                'data': decrypted_data
            }
            
        except Exception as e:
            logger.error(f"Error decrypting QMC file {file_path}: {e}")
            return {
                'success': False,
                'error': f"QMC decryption failed: {e}"
            }
    
    @staticmethod
    def _decrypt_ncm(file_path, output_dir):
        """Decrypt NCM format files (NetEase Cloud Music)"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # NCM files have a specific header structure
            # For now, we'll implement a basic NCM decryption
            # This is a simplified version - full NCM decryption is more complex
            
            # Skip NCM header (first 8 bytes)
            if len(data) < 8:
                raise ValueError("Invalid NCM file: too short")
            
            # Extract the encrypted audio data (simplified)
            encrypted_data = data[8:]
            
            # Basic NCM decryption (simplified)
            # In a full implementation, this would decrypt using the NCM algorithm
            decrypted_data = MusicDecryptor._basic_ncm_decrypt(encrypted_data)
            
            # Detect format from decrypted content
            format_ext = MusicDecryptor._detect_audio_format_from_data(decrypted_data)
            
            # Create output filename
            base_name = file_path.stem
            output_filename = f"{base_name}{format_ext}"
            output_path = Path(output_dir) / output_filename
            
            # Handle filename conflicts
            counter = 1
            original_output_path = output_path
            while output_path.exists():
                name_parts = original_output_path.stem, f"({counter})", original_output_path.suffix
                output_path = original_output_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                counter += 1
            
            # Write decrypted data
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            logger.info(f"Successfully decrypted NCM file: {file_path.name} -> {output_path.name}")
            
            return {
                'success': True,
                'file': str(output_path),
                'ext': output_path.suffix[1:],
                'data': decrypted_data
            }
            
        except Exception as e:
            logger.error(f"Error decrypting NCM file {file_path}: {e}")
            return {
                'success': False,
                'error': f"NCM decryption failed: {e}"
            }
    
    @staticmethod
    def _basic_ncm_decrypt(data):
        """Basic NCM decryption (simplified implementation)"""
        # This is a placeholder for actual NCM decryption
        # In a real implementation, this would use the NCM decryption algorithm
        # For now, we'll return the data as-is (no actual decryption)
        return data
    
    @staticmethod
    def _handle_unknown_format(file_path, output_dir):
        """Handle unknown or unsupported formats"""
        try:
            # For unknown formats, try to detect and copy
            format_ext = MusicDecryptor._detect_audio_format_from_file(file_path)
            
            base_name = file_path.stem
            output_filename = f"{base_name}{format_ext}"
            output_path = Path(output_dir) / output_filename
            
            # Handle filename conflicts
            counter = 1
            original_output_path = output_path
            while output_path.exists():
                name_parts = original_output_path.stem, f"({counter})", original_output_path.suffix
                output_path = original_output_path.parent / f"{name_parts[0]}{name_parts[1]}{name_parts[2]}"
                counter += 1
            
            # Copy the file
            shutil.copy2(file_path, output_path)
            
            logger.warning(f"Unsupported format: {file_path.name} - copied as {output_path.name}")
            
            return {
                'success': True,
                'file': str(output_path),
                'ext': output_path.suffix[1:],
                'data': b'',
                'warning': f'Format {file_path.suffix} not fully supported - file copied as-is'
            }
            
        except Exception as e:
            logger.error(f"Error handling unknown format {file_path}: {e}")
            return {
                'success': False,
                'error': f"Unknown format handling failed: {e}"
            }
    
    @staticmethod
    def _detect_audio_format_from_data(data):
        """Detect audio format from data bytes"""
        if len(data) < 12:
            return '.mp3'  # Default
        
        header = data[:12]
        
        # Check for common audio format signatures
        if header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3'):
            return '.mp3'
        elif header.startswith(b'fLaC'):
            return '.flac'
        elif header.startswith(b'OggS'):
            return '.ogg'
        elif header.startswith(b'RIFF') and header[8:12] == b'WAVE':
            return '.wav'
        elif header.startswith(b'\x00\x00\x00') and header[4:8] in [b'ftyp', b'M4A ', b'M4V ', b'isom']:
            return '.m4a'
        elif header.startswith(b'\xff\xf1') or header.startswith(b'\xff\xf9'):
            return '.aac'
        else:
            return '.mp3'  # Default
    
    @staticmethod
    def _detect_audio_format_from_file(file_path):
        """Detect audio format from file"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
            
            return MusicDecryptor._detect_audio_format_from_data(header)
        except Exception as e:
            logger.warning(f"Error detecting audio format for {file_path}: {e}")
            return '.mp3'  # Default

# Platform detection and configuration
def get_platform_info():
    """Get platform-specific information"""
    system = platform.system().lower()
    return {
        'system': system,
        'is_windows': system == 'windows',
        'is_mac': system == 'darwin',
        'is_linux': system == 'linux',
        'encoding': 'utf-8'  # Use UTF-8 consistently across platforms
    }

PLATFORM = get_platform_info()

# Configuration - Use pathlib for cross-platform compatibility
_BASE_DIR = Path(__file__).parent.parent  # Go up one level from bin directory
CONFIG = {
    'library_path': str(_BASE_DIR / 'Library'),
    'new_path': str(_BASE_DIR / 'New'),
    'duplicate_path': str(_BASE_DIR / 'Duplicate'),
    'trash_path': str(_BASE_DIR / 'Trash'),
    'unlocked_path': str(_BASE_DIR / 'Unlocked'),  # New folder for decrypted files
    'json_file': str(Path(__file__).parent / 'mayi-music-list.json'),  # JSON file in current directory
    'thumbnails_dir': str(Path(__file__).parent / 'thumbnails'),  # Save thumbnails in the current scripts directory
    'supported_formats': {'.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg', '.wma'},
    'encrypted_formats': {'.ncm', '.qmc0', '.qmc3', '.qmcflac', '.qmcogg', '.mflac', '.mgg', '.bkcmp3', '.bkcflac', '.tkm', '.xm', '.mflac0', '.mflac1', '.mgg0', '.mgg1', '.666c9668', '.m4a', '.cc', '.m4a', '.m4b', '.m4p', '.m4v', '.m4s', '.3gp', '.3g2', '.f4v', '.f4a', '.f4b', '.f4p', '.m4a', '.m4b', '.m4p', '.m4v', '.m4s', '.3gp', '.3g2', '.f4v', '.f4a', '.f4b', '.f4p'},
    'max_workers': max(2, min(8, os.cpu_count() or 4)),  # Auto-detect optimal worker count (2-8 range)
    'unlock_max_workers': None,  # Use None for auto-detection, or set a specific number
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
                    CONFIG['duplicate_path'], CONFIG['trash_path'], CONFIG['unlocked_path']]:
            Path(path).mkdir(parents=True, exist_ok=True)
        
        # Create thumbnails directory
        Path(CONFIG['thumbnails_dir']).mkdir(parents=True, exist_ok=True)
    
    def load_catalog(self):
        """Load the music catalog from JSON file"""
        try:
            catalog_path = Path(CONFIG['json_file'])
            if catalog_path.exists():
                with open(catalog_path, 'r', encoding='utf-8') as f:
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
            catalog_path = Path(CONFIG['json_file'])
            # Ensure directory exists
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            with open(catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            logger.info(f"Catalog saved successfully to {catalog_path} with {len(self.catalog['songs'])} songs")
        except Exception as e:
            logger.error(f"Error saving catalog: {e}")
            raise
    
    def _sanitize_filename(self, filename):
        """Sanitize filename for cross-platform compatibility"""
        import re
        
        # Remove/replace characters that are problematic on different OS
        if PLATFORM['is_windows']:
            # Windows has more restrictions
            invalid_chars = r'[<>:"/\\|?*]'
            filename = re.sub(invalid_chars, '_', filename)
        else:
            # Unix-like systems (macOS, Linux)
            filename = filename.replace('/', '_')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure it's not empty
        if not filename:
            filename = 'unnamed'
        
        # Limit length to 255 characters (filesystem limit)
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename
    
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
            # Handle Unicode filenames properly across platforms
            file_path = Path(file_path)
            filename_stem = file_path.stem
            
            # Sanitize filename for cross-platform compatibility
            safe_filename = self._sanitize_filename(filename_stem)
            thumbnail_path = Path(CONFIG['thumbnails_dir']) / f"{safe_filename}.jpg"
            
            # Check if thumbnail already exists
            if thumbnail_path.exists():
                logger.info(f"Thumbnail already exists for {filename_stem}")
                return True
            
            # Extract artwork from different tag formats
            artwork = None
            
            # Check for FLAC pictures first (they have a special pictures attribute)
            if hasattr(audio, 'pictures') and audio.pictures:
                try:
                    # FLAC files store pictures in a pictures list
                    artwork = audio.pictures[0]  # Get the first picture
                    logger.info(f"Found FLAC picture for {filename_stem}")
                except Exception as e:
                    logger.warning(f"Failed to get FLAC picture for {filename_stem}: {e}")
            
            # Try different tag formats if no FLAC pictures found
            elif hasattr(audio, 'tags') and audio.tags:
                tags = audio.tags
                
                # MP3/ID3 tags
                if hasattr(tags, 'getall'):
                    for key in ['APIC:', 'APIC:cover', 'APIC:0']:
                        try:
                            artwork_data = tags.getall(key)
                            if artwork_data:
                                artwork = artwork_data[0]
                                logger.info(f"Found ID3 artwork for {filename_stem}")
                                break
                        except:
                            continue
                
                # FLAC/Vorbis tags (fallback for embedded base64 pictures)
                elif hasattr(tags, 'get'):
                    for key in ['metadata_block_picture', 'METADATA_BLOCK_PICTURE']:
                        try:
                            artwork_data = tags.get(key)
                            if artwork_data:
                                if isinstance(artwork_data, list):
                                    artwork = artwork_data[0]
                                else:
                                    artwork = artwork_data
                                logger.info(f"Found Vorbis artwork for {filename_stem}")
                                break
                        except:
                            continue
                
                # M4A/MP4 tags
                elif 'covr' in tags:
                    try:
                        artwork = tags['covr'][0]
                        logger.info(f"Found M4A artwork for {filename_stem}")
                    except:
                        pass
            
            if artwork:
                try:
                    # Handle different artwork formats
                    if hasattr(artwork, 'data'):
                        # mutagen APIC object or FLAC Picture object
                        image_data = artwork.data
                        logger.info(f"Extracted artwork data ({len(artwork.data)} bytes) for {filename_stem}")
                    elif isinstance(artwork, bytes):
                        # Raw bytes
                        image_data = artwork
                        logger.info(f"Using raw artwork bytes ({len(artwork)} bytes) for {filename_stem}")
                    elif hasattr(artwork, 'picture') and hasattr(artwork.picture, 'data'):
                        # Some FLAC formats might have nested picture data
                        image_data = artwork.picture.data
                        logger.info(f"Extracted nested picture data for {filename_stem}")
                    else:
                        # Try to get data attribute or use as-is
                        image_data = getattr(artwork, 'data', artwork)
                        if isinstance(image_data, bytes):
                            logger.info(f"Using fallback artwork data for {filename_stem}")
                        else:
                            logger.warning(f"Unknown artwork format for {filename_stem}: {type(artwork)}")
                            return False
                    
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
            safe_filename = self._sanitize_filename(filename_stem)
            thumbnail_path = Path(CONFIG['thumbnails_dir']) / f"{safe_filename}.jpg"
            
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
    
    def unlock_music_files(self):
        """Unlock encrypted music files from the Unlocked folder and move to New folder"""
        try:
            # Check if decryptor is available
            if not decryptor_available:
                return {
                    'success': False,
                    'error': 'Music decryption is not available. Please install the decryptor dependencies: pip install cryptography requests'
                }
            
            unlocked_path = Path(CONFIG['unlocked_path'])
            new_path = Path(CONFIG['new_path'])
            
            if not unlocked_path.exists():
                return {
                    'success': True,
                    'message': 'No Unlocked folder found',
                    'processed_files': 0,
                    'successful_unlocks': 0,
                    'failed_unlocks': 0,
                    'moved_to_new': 0
                }
            
            # Find all encrypted music files
            encrypted_files = []
            for file_path in unlocked_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in CONFIG['encrypted_formats']:
                    encrypted_files.append(file_path)
            
            if not encrypted_files:
                return {
                    'success': True,
                    'message': 'No encrypted music files found in Unlocked folder',
                    'processed_files': 0,
                    'successful_unlocks': 0,
                    'failed_unlocks': 0,
                    'moved_to_new': 0
                }
            
            successful_unlocks = 0
            failed_unlocks = 0
            moved_to_new = 0
            failed_files = []
            
            # Use multiple workers for faster processing
            # Determine optimal worker count for unlocking
            unlock_workers = CONFIG.get('unlock_max_workers')
            if unlock_workers is None:
                # Auto-detect based on CPU count and file count
                cpu_count = os.cpu_count() or 4
                unlock_workers = max(2, min(cpu_count, len(encrypted_files), 8))
            else:
                unlock_workers = min(unlock_workers, len(encrypted_files))
            
            # Start timing for performance measurement
            start_time = datetime.now()
            logger.info(f"Starting to unlock {len(encrypted_files)} encrypted music files using {unlock_workers} workers (CPU cores: {os.cpu_count()})")
            
            def unlock_single_file(file_path):
                """Unlock a single encrypted music file"""
                try:
                    # Detect file format
                    fmt = MusicDecryptor.detect_file_format(str(file_path))
                    if fmt == "unknown":
                        logger.warning(f"Unsupported file format: {file_path.suffix}")
                        return {
                            'success': False,
                            'file': str(file_path),
                            'error': f"Unsupported format: {file_path.suffix}"
                        }
                    
                    logger.info(f"Unlocking {file_path.name} (format: {fmt})")
                    
                    # Decrypt the file
                    result = MusicDecryptor.decrypt_file(str(file_path), str(new_path))
                    
                    if result and result.get('success') and result.get('file'):
                        logger.info(f"Successfully unlocked: {file_path.name} -> {result['file']}")
                        
                        # Log warning if this is a placeholder implementation
                        if result.get('warning'):
                            logger.warning(f"Warning for {file_path.name}: {result['warning']}")
                        
                        # Keep the original encrypted file in the Unlocked folder
                        logger.info(f"Original encrypted file kept: {file_path.name}")
                        
                        return {
                            'success': True,
                            'file': str(file_path),
                            'output_file': result['file'],
                            'moved_to_new': True
                        }
                    else:
                        error_msg = result.get('error', 'Decryption failed') if result else 'Decryption failed'
                        logger.error(f"Failed to unlock: {file_path.name}: {error_msg}")
                        return {
                            'success': False,
                            'file': str(file_path),
                            'error': error_msg
                        }
                        
                except Exception as e:
                    logger.error(f"Error unlocking {file_path.name}: {e}")
                    return {
                        'success': False,
                        'file': str(file_path),
                        'error': str(e)
                    }
            
            # Process files concurrently using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=unlock_workers) as executor:
                # Submit all tasks
                future_to_file = {executor.submit(unlock_single_file, file_path): file_path 
                                 for file_path in encrypted_files}
                
                # Collect results as they complete with progress tracking
                from concurrent.futures import as_completed
                completed = 0
                total = len(encrypted_files)
                
                for future in as_completed(future_to_file):
                    completed += 1
                    try:
                        result = future.result()
                        if result['success']:
                            successful_unlocks += 1
                            if result.get('moved_to_new'):
                                moved_to_new += 1
                        else:
                            failed_unlocks += 1
                            failed_files.append({
                                'file': result['file'],
                                'error': result['error']
                            })
                        
                        # Log progress every 10% or every 5 files, whichever is smaller
                        progress_interval = max(1, min(5, total // 10))
                        if completed % progress_interval == 0 or completed == total:
                            progress_pct = (completed / total) * 100
                            logger.info(f"Progress: {completed}/{total} files processed ({progress_pct:.1f}%) - "
                                       f"Success: {successful_unlocks}, Failed: {failed_unlocks}")
                            
                    except Exception as e:
                        file_path = future_to_file[future]
                        failed_unlocks += 1
                        failed_files.append({
                            'file': str(file_path),
                            'error': f"Worker exception: {str(e)}"
                        })
                        logger.error(f"Worker exception for {file_path.name}: {e}")
            
            # Calculate timing and performance metrics
            end_time = datetime.now()
            elapsed_time = end_time - start_time
            elapsed_seconds = elapsed_time.total_seconds()
            
            # Calculate processing rate
            if elapsed_seconds > 0:
                files_per_second = len(encrypted_files) / elapsed_seconds
                avg_time_per_file = elapsed_seconds / len(encrypted_files)
                message = (f"Unlock process completed in {elapsed_seconds:.2f}s: "
                          f"{successful_unlocks} successful, {failed_unlocks} failed "
                          f"({files_per_second:.2f} files/sec, {avg_time_per_file:.2f}s/file avg)")
            else:
                message = f"Unlock process completed: {successful_unlocks} successful, {failed_unlocks} failed"
            if successful_unlocks > 0:
                message += f", {moved_to_new} files moved to New folder"
                message += f" (original files kept in Unlocked folder)"
            
            logger.info(message)
            
            return {
                'success': True,
                'message': message,
                'processed_files': len(encrypted_files),
                'successful_unlocks': successful_unlocks,
                'failed_unlocks': failed_unlocks,
                'moved_to_new': moved_to_new,
                'failed_files': failed_files,
                'performance': {
                    'elapsed_seconds': elapsed_seconds,
                    'files_per_second': files_per_second if elapsed_seconds > 0 else 0,
                    'avg_time_per_file': avg_time_per_file if elapsed_seconds > 0 else 0,
                    'workers_used': unlock_workers,
                    'cpu_cores': os.cpu_count()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in unlock_music_files: {e}")
            return {'success': False, 'error': str(e)}
    
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

@app.route('/api/unlock-music', methods=['POST'])
def unlock_music():
    """Unlock encrypted music files"""
    result = manager.unlock_music_files()
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
    print(f"🔓 Unlocked files: {CONFIG['unlocked_path']}")
    print(f"🔄 Duplicates: {CONFIG['duplicate_path']}")
    print(f"🗑️  Trash: {CONFIG['trash_path']}")
    print(f"📝 Log file: {CONFIG['log_file']}")
    print(f"💾 Catalog: {CONFIG['json_file']}")
    
    # Show decryptor status
    if decryptor_available:
        print("🔓 Music decryption: ✅ Available")
    else:
        print("🔓 Music decryption: ❌ Not available (install: pip install cryptography requests)")
    
    print()
    print("🌐 Starting web interface...")
    print("📱 Open your browser to: http://localhost:8088")
    print("⏹️  Press Ctrl+C to stop")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=8088)
