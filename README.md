# 🎵 Music Library Management System

A web-based music library management system with automatic metadata extraction, thumbnail generation, and built-in audio player.

## ✨ Features

- **📚 Music Library Browser** - View all music with search, filtering, and pagination
- **🎵 Built-in Audio Player** - Play songs directly in the browser
- **🖼️ Thumbnail Extraction** - Automatic album artwork extraction and display
- **🔍 Smart Search & Filter** - Search by title, artist, album with format and duration filters
- **📊 Real-time Statistics** - Library overview with file counts and sizes
- **📤 Add New Music** - Scan and add music from the New directory
- **🔄 Library Scanning** - Update catalog and extract missing metadata

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supported audio formats: MP3, FLAC, M4A, WAV, AAC, OGG, WMA

### Installation & Launch

#### **macOS/Linux:**
```bash
cd music_library_tools
./launch_unified.sh
```

#### **Windows:**
```cmd
cd music_library_tools
launch_unified.bat
```

#### **Manual Launch:**
```bash
cd music_library_tools
python launch_unified.py
```

The system will automatically:
- Create a virtual environment
- Install required dependencies
- Start the web server
- Open your browser to http://localhost:8088

## 📁 Project Structure

```
Music Lib Tools/
├── music_library_tools/          # Main application
│   ├── unified_web_interface.py  # Flask web application
│   ├── launch_unified.py         # Python launcher
│   ├── launch_unified.sh         # macOS/Linux launcher
│   ├── launch_unified.bat        # Windows launcher
│   ├── requirements.txt          # Python dependencies
│   ├── templates/index.html      # Web interface
│   ├── thumbnails/               # Album artwork cache
│   └── mayi-music-list.json      # Music catalog database
├── Library/                      # Your music files
├── New/                          # New files to add
└── Trash/                        # Deleted files
```

## 🎯 How to Use

### **1. Browse Your Library**
- View all music files with pagination (12-96 items per page)
- Search by title, artist, or album
- Filter by format (MP3, FLAC) and duration
- Click play button to start audio playback

### **2. Add New Music**
- Place music files in the `New/` directory
- Click "Add New Music" to scan and add them to your library
- Files are automatically processed with metadata extraction

### **3. Scan Library**
- Click "Scan Library" to update the catalog
- Extracts missing metadata and thumbnails
- Updates file information

### **4. Audio Player**
- Built-in player at the bottom of the page
- Play/pause, previous/next, volume control
- Progress bar with seeking capability

## 🔧 Configuration

The system uses these default paths:
- **Music Library:** `../Library/`
- **New Files:** `../New/`
- **Trash:** `../Trash/`
- **Thumbnails:** `thumbnails/` (in the scripts folder)
- **Catalog Database:** `mayi-music-list.json`

## 🛠️ Technical Details

### **Supported Audio Formats**
- MP3, FLAC, M4A, WAV, AAC, OGG, WMA

### **Metadata Extraction**
- Title, Artist, Album, Duration, Bitrate
- Automatic thumbnail extraction from audio files
- File size and format detection

### **Web Interface**
- Responsive design for desktop and mobile
- Real-time search and filtering
- Pagination for large libraries
- Base64-encoded thumbnails for fast loading

## 🐛 Troubleshooting

### **Port Already in Use**
The system runs on port 8088. If busy, modify the port in `unified_web_interface.py`.

### **Missing Dependencies**
The launcher scripts automatically install dependencies. If issues occur:
```bash
source music_env_darwin/bin/activate  # macOS
# or
source music_env_linux/bin/activate   # Linux
# or
music_env_windows\Scripts\activate    # Windows
pip install -r requirements.txt
```

### **Virtual Environment Issues**
If the environment is corrupted, delete it and restart:
```bash
rm -rf music_env_*
./launch_unified.sh  # or launch_unified.bat on Windows
```

## 📝 License

Personal use project. Feel free to modify for your needs.

---

**🎵 Enjoy your organized music library!**
