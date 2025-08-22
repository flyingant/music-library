# 🎵 MaYi's Music Library Management System

A comprehensive web-based music library management system with encryption/decryption support, automatic metadata extraction, thumbnail generation, and built-in audio player.

> **✨ Complete Music Management Solution**  
> Organize, decrypt, and enjoy your music collection with a modern web interface featuring multi-threaded processing, automatic duplicate detection, and cross-platform compatibility.

## ✨ Key Features

- **🔓 Music Decryption** - Decrypt NCM, QMC and other encrypted music formats with multi-threaded processing
- **📚 Smart Library Browser** - Search, filter, and paginate through your music collection  
- **🎵 Built-in Audio Player** - Stream music directly in your browser with full controls
- **🖼️ Automatic Thumbnails** - Extract and display album artwork from audio files
- **🔄 Intelligent Workflow** - Combined "Add Music + Check Duplicates" streamlines organization
- **📊 Real-time Statistics** - Live library overview with file counts, formats, and sizes
- **⚡ Multi-threaded Processing** - Fast file operations using CPU cores efficiently
- **🌐 Cross-platform** - Works on Windows, macOS, and Linux

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supported audio formats: MP3, FLAC, M4A, WAV, AAC, OGG, WMA

### Installation & Launch

#### **macOS/Linux:**
```bash
cd music-library-tool/bin
./launch_unified.sh
```

#### **Windows:**
```cmd
cd music-library-tool\bin
launch_unified.bat
```

#### **Manual Launch:**
```bash
cd music-library-tool/bin
python launch_unified.py
```

The system will automatically:
- Create a virtual environment
- Install required dependencies
- Start the web server
- Open your browser to http://localhost:8088

## 📁 Project Structure

```
music-library-tool/
├── bin/                          # Main application
│   ├── unified_web_interface.py  # Flask web application with integrated decryptor
│   ├── launch_unified.py         # Python launcher with auto-setup
│   ├── launch_unified.sh         # macOS/Linux launcher
│   ├── launch_unified.bat        # Windows launcher
│   ├── requirements.txt          # Python dependencies
│   ├── templates/index.html      # Modern responsive web interface
│   ├── thumbnails/               # Album artwork cache
│   ├── music_env_*              # Platform-specific virtual environments
│   └── mayi-music-list.json      # Music catalog database
├── Library/                      # Your organized music files
├── New/                          # New files to add to library
├── Duplicate/                    # Automatically detected duplicates
├── Unlocked/                     # Encrypted files to decrypt
└── Trash/                        # Deleted/corrupted files
```

## 🎯 How to Use

### **1. 🔓 Unlock Encrypted Music**
- Place encrypted files (.ncm, .qmc, etc.) in the `Unlocked/` directory
- Click "Unlock Music" for fast multi-threaded decryption
- Decrypted files automatically move to `New/` with embedded artwork

### **2. 📁 Add Music + Check Duplicates**
- Place music files in the `New/` directory  
- Click "Add Music + Check Duplicates" for streamlined processing
- Automatically adds files and detects/moves duplicates in one operation

### **3. 📚 Browse Your Library**
- Search by title, artist, or album with real-time filtering
- Filter by format (MP3, FLAC) and duration ranges
- View with pagination (24-96 items per page)
- Click thumbnails to play music instantly

### **4. 🎵 Built-in Audio Player**
- Modern player with full controls (play/pause, seek, volume)
- Automatic track progression and playlist support
- Responsive design for desktop and mobile

## 🔧 Configuration

The system uses these default paths:
- **Music Library:** `../Library/` (organized music collection)
- **New Files:** `../New/` (files to add to library)
- **Encrypted Files:** `../Unlocked/` (files to decrypt)
- **Duplicates:** `../Duplicate/` (automatically detected duplicates)
- **Trash:** `../Trash/` (deleted/corrupted files)
- **Thumbnails:** `thumbnails/` (album artwork cache)
- **Catalog Database:** `mayi-music-list.json` (metadata index)

## 🛠️ Technical Details

### **Supported Formats**
- **Audio:** MP3, FLAC, M4A, WAV, AAC, OGG, WMA
- **Encrypted:** NCM (Netease), QMC (QQ Music), and variants

### **Advanced Features**
- **Multi-threaded Processing:** Utilizes CPU cores for fast decryption (up to 8x speedup)
- **Automatic Artwork:** Downloads and embeds album artwork from metadata
- **Smart Duplicate Detection:** Hash-based and name-based duplicate identification
- **Cross-platform Compatibility:** Windows, macOS, Linux support
- **Metadata Extraction:** Title, Artist, Album, Duration, Bitrate, File size

### **Web Interface**
- **Modern Design:** Responsive layout for desktop and mobile
- **Real-time Features:** Live search, filtering, and statistics
- **Performance Optimized:** Pagination, thumbnail caching, efficient loading
- **Audio Streaming:** Built-in player with seek controls and playlist support

## 🐛 Troubleshooting

### **Port Already in Use**
The system runs on port 8088. If busy, modify the port in `unified_web_interface.py`.

### **Missing Dependencies**
The launcher scripts automatically install dependencies. If issues occur:
```bash
cd bin
source music_env_darwin/bin/activate    # macOS
source music_env_linux/bin/activate     # Linux  
music_env_windows\Scripts\activate      # Windows
pip install -r requirements.txt
```

### **Virtual Environment Issues**
If the environment is corrupted, delete it and restart:
```bash
cd bin
rm -rf music_env_*
../launch_unified.sh  # or launch_unified.bat on Windows
```

## 📝 License

Personal use project. Feel free to modify for your needs.

---

**🎵 Enjoy your organized music library!**
