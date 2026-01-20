import os
import zipfile
import shutil
import time
import random
from datetime import datetime
import sys
import threading
import configparser
import keyboard
from pathlib import Path

def get_settings_path():
    """Determine the path to the settings file"""
    # If the script is running from an exe
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(__file__)
    
    return os.path.join(base_dir, 'Settings.ini')

def expand_path(path):
    """Expand special paths like %APPDATA% and ~"""
    # Replace %USERPROFILE%, %APPDATA%, etc.
    if '%' in path:
        path = os.path.expandvars(path)
    
    # Replace ~ with home directory
    path = os.path.expanduser(path)
    
    # Normalize path (remove .., etc.)
    path = os.path.normpath(path)
    
    return path

def get_default_paths():
    """Return default paths depending on the OS"""
    if sys.platform == 'win32':
        # For Windows
        user_dir = os.path.expanduser('~')
        appdata_local = os.getenv('LOCALAPPDATA', os.path.join(user_dir, 'AppData', 'Local'))
        documents = os.path.join(user_dir, 'Documents')
        
        default_save_dir = os.path.join(appdata_local, 'Hinterland')
        default_backup_dir = os.path.join(documents, 'TLD_Backups')
        
    elif sys.platform == 'darwin':
        # For macOS
        user_dir = os.path.expanduser('~')
        default_save_dir = os.path.join(user_dir, 'Library', 'Application Support', 'Hinterland')
        default_backup_dir = os.path.join(user_dir, 'Documents', 'TLD_Backups')
        
    else:
        # For Linux and others
        user_dir = os.path.expanduser('~')
        default_save_dir = os.path.join(user_dir, '.local', 'share', 'Hinterland')
        default_backup_dir = os.path.join(user_dir, 'TLD_Backups')
    
    return default_save_dir, default_backup_dir

def load_settings():
    """Load settings from Settings.ini file"""
    settings_path = get_settings_path()
    config = configparser.ConfigParser()
    
    # Get default paths
    default_save_dir, default_backup_dir = get_default_paths()
    
    # Default values
    default_settings = {
        'Paths': {
            'save_dir': default_save_dir,
            'backup_dir': default_backup_dir
        },
        'Backup': {
            'game_name': "TheLongDark_2.02",
            'max_backups': "50",
            'backup_interval': "20"  # in minutes
        },
        'Advanced': {
            'log_level': "INFO",
            'compress_level': "6"
        }
    }
    
    # If settings file doesn't exist, create it with default values
    if not os.path.exists(settings_path):
        print(f"Settings file not found. Creating new file: {settings_path}")
        config.read_dict(default_settings)
        with open(settings_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print("\n" + "="*60)
        print("📄 Settings.ini file created with default paths:")
        print("="*60)
        print(f"📁 Save folder: {default_save_dir}")
        print(f"💾 Backup folder:    {default_backup_dir}")
        print("\n⚠️  Check the paths and modify them if necessary.")
        print("Then restart the program.")
        print("="*60)
        
        if sys.platform == 'win32':
            os.startfile(settings_path)
        
        input("\nPress Enter to exit...")
        sys.exit(0)
    
    # Load settings
    config.read(settings_path, encoding='utf-8')
    
    # Check for all necessary sections and keys
    for section, keys in default_settings.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, default_value in keys.items():
            if not config.has_option(section, key):
                config.set(section, key, default_value)
    
    # Save if new parameters were added
    with open(settings_path, 'w', encoding='utf-8') as f:
        config.write(f)
    
    # Expand paths (process %VAR% and ~)
    save_dir = expand_path(config.get('Paths', 'save_dir').strip('"\' '))
    backup_dir = expand_path(config.get('Paths', 'backup_dir').strip('"\' '))
    
    # Convert settings to appropriate types
    settings = {
        'SAVE_DIR': save_dir,
        'BACKUP_DIR': backup_dir,
        'GAME_NAME': config.get('Backup', 'game_name'),
        'MAX_BACKUPS': config.getint('Backup', 'max_backups'),
        'BACKUP_INTERVAL': config.getint('Backup', 'backup_interval'),
        'LOG_LEVEL': config.get('Advanced', 'log_level'),
        'COMPRESS_LEVEL': config.getint('Advanced', 'compress_level')
    }
    
    return settings, settings_path

def create_backup(source_dir, backup_dir, game_name, max_backups=50, compress_level=6):
    """
    Create an archive with a backup of the saves folder
    """
    try:
        # Check if source folder exists
        if not os.path.exists(source_dir):
            print(f"✗ Save folder not found: {source_dir}")
            print("   Check the path in Settings.ini or create this folder")
            return False
        
        # Create backup folder if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
            print(f"✓ Backup folder created: {backup_dir}")
        
        # Check if there are files to backup
        files_to_backup = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                files_to_backup.append(os.path.join(root, file))
        
        if not files_to_backup:
            print(f"⚠️  No files in save folder: {source_dir}")
            return False
        
        # Generate filename with date and time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{game_name}_backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create ZIP archive with specified compression level
        compression = zipfile.ZIP_DEFLATED
        compress_level = min(max(compress_level, 0), 9)  # Limit to 0-9
        
        with zipfile.ZipFile(backup_path, 'w', compression) as zipf:
            zipf.comment = f"Backup of {game_name} saves. Created {datetime.now()}".encode()
            
            for file_path in files_to_backup:
                try:
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                except Exception as e:
                    print(f"  ⚠️  Failed to add file {file_path}: {e}")
        
        # Check the size of the created archive
        if os.path.exists(backup_path):
            size = os.path.getsize(backup_path)
            size_mb = size / (1024 * 1024)
            print(f"✓ Backup created: {backup_filename}")
            print(f"  📊 Size: {size_mb:.2f} MB, files: {len(files_to_backup)}")
        else:
            print(f"✗ Failed to create backup: {backup_path}")
            return False
        
        # Clean up old backups
        cleanup_old_backups(backup_dir, game_name, max_backups)
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return False

def cleanup_old_backups(backup_dir, game_name, max_backups=50):
    """
    Remove old backups, keeping only the latest max_backups
    """
    try:
        # Get list of backups
        backups = []
        for file in os.listdir(backup_dir):
            if file.startswith(f"{game_name}_backup_") and file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                backups.append((file_path, os.path.getctime(file_path)))
        
        # Sort by creation date (oldest first)
        backups.sort(key=lambda x: x[1])
        
        # Remove excess backups
        removed_count = 0
        while len(backups) > max_backups:
            old_backup = backups.pop(0)
            try:
                os.remove(old_backup[0])
                removed_count += 1
                print(f"  🗑️  Old backup deleted: {os.path.basename(old_backup[0])}")
            except Exception as e:
                print(f"  ⚠️  Failed to delete {old_backup[0]}: {e}")
        
        if removed_count > 0:
            print(f"  📊 Old backups deleted: {removed_count}")
            
    except Exception as e:
        print(f"  ⚠️  Error cleaning up old backups: {e}")

def manual_backup_handler(backup_func, source_dir, backup_dir, game_name, max_backups, compress_level):
    """Handler for manual backup creation"""
    def handler():
        print("\n" + "="*60)
        print("🔄 Manual backup triggered by user (F5)")
        print("="*60)
        backup_func(source_dir, backup_dir, game_name, max_backups, compress_level)
        print(f"\n⏰ Next automatic backup in {backup_interval} minutes...")
        print("-"*60)
    
    return handler

def auto_backup_scheduler(backup_func, source_dir, backup_dir, game_name, max_backups, interval_minutes, compress_level):
    """Scheduler for automatic backups"""
    try:
        while True:
            # Fixed interval from settings
            interval = interval_minutes * 60  # in seconds
            
            # Wait for the specified interval
            print(f"\n⏰ Next automatic backup in {interval_minutes} minutes...")
            time.sleep(interval)
            
            # Create backup
            print("\n" + "="*60)
            print("🤖 Automatic backup on schedule")
            print("="*60)
            backup_func(source_dir, backup_dir, game_name, max_backups, compress_level)
            
    except KeyboardInterrupt:
        print("\n🛑 Backup scheduler stopped")
        return

def open_settings_file():
    """Open settings file in text editor"""
    settings_path = get_settings_path()
    try:
        if os.path.exists(settings_path):
            if sys.platform == 'win32':
                os.startfile(settings_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{settings_path}"')
            else:
                os.system(f'xdg-open "{settings_path}"')
            
            print(f"\n📄 Settings file opened: {settings_path}")
            print("⚠️  Restart the program after changing settings")
        else:
            print(f"✗ Settings file not found: {settings_path}")
    except Exception as e:
        print(f"✗ Failed to open settings file: {e}")

def show_help():
    """Show usage help"""
    print("\n" + "="*60)
    print("📖 USAGE HELP")
    print("="*60)
    print("\n✨ Hotkeys:")
    print("  F5  - Create backup now")
    print("  F9  - Open settings file Settings.ini")
    print("  F10 - Show current settings")
    print("  F1  - Show this help")
    print("  Ctrl+C - Exit program")
    
    print("\n📁 Paths in Settings.ini:")
    print("  You can use special variables:")
    print("  %USERPROFILE% - user folder (Windows)")
    print("  %APPDATA%     - Roaming AppData (Windows)")
    print("  %LOCALAPPDATA% - Local AppData (Windows)")
    print("  ~            - home folder (Linux/Mac/Windows)")
    
    print("\n📝 Path examples:")
    print("  Windows:  C:\\Users\\Name\\Documents\\TLD_Backups")
    print("            %USERPROFILE%\\Documents\\TLD_Backups")
    print("  Linux:    /home/name/TLD_Backups")
    print("            ~/TLD_Backups")
    print("="*60)

def main():
    # Load settings
    settings, settings_path = load_settings()
    
    SAVE_DIR = settings['SAVE_DIR']
    BACKUP_DIR = settings['BACKUP_DIR']
    GAME_NAME = settings['GAME_NAME']
    MAX_BACKUPS = settings['MAX_BACKUPS']
    BACKUP_INTERVAL = settings['BACKUP_INTERVAL']
    COMPRESS_LEVEL = settings['COMPRESS_LEVEL']
    
    # Global variable for use in handler
    global backup_interval
    backup_interval = BACKUP_INTERVAL
    
    print(f"⚙️  Settings loaded from: {settings_path}")
    print("="*60)
    print(f"🎮 Save backup tool for: {GAME_NAME}")
    print(f"📁 Save folder: {SAVE_DIR}")
    print(f"💾 Backup folder: {BACKUP_DIR}")
    print(f"📊 Max backups: {MAX_BACKUPS}")
    print(f"⏱️  Backup interval: {BACKUP_INTERVAL} minutes")
    print(f"🗜️  Compression level: {COMPRESS_LEVEL}/9")
    print("="*60)
    print("✨ Hotkeys (F1 - help)")
    print("="*60)
    
    try:
        # Set up hotkeys
        keyboard.add_hotkey('f5', 
                           manual_backup_handler(create_backup, SAVE_DIR, BACKUP_DIR, 
                                               GAME_NAME, MAX_BACKUPS, COMPRESS_LEVEL),
                           suppress=True)
        
        keyboard.add_hotkey('f9', open_settings_file, suppress=True)
        
        def show_settings():
            print("\n" + "="*60)
            print("📋 Current settings:")
            print("="*60)
            print(f"  Save folder: {SAVE_DIR}")
            print(f"  Backup folder:    {BACKUP_DIR}")
            print(f"  Game name:         {GAME_NAME}")
            print(f"  Max backups:    {MAX_BACKUPS}")
            print(f"  Interval:         {BACKUP_INTERVAL} minutes")
            print(f"  Compression:           {COMPRESS_LEVEL}/9")
            print(f"  Settings file:    {settings_path}")
            print("="*60)
        
        keyboard.add_hotkey('f10', show_settings, suppress=True)
        keyboard.add_hotkey('f1', show_help, suppress=True)
        
        print(f"\n✅ Hotkeys activated")
        print(f"⏳ First automatic backup in {BACKUP_INTERVAL} minutes...\n")
        
        # Start automatic backup scheduler in separate thread
        scheduler_thread = threading.Thread(
            target=auto_backup_scheduler,
            args=(create_backup, SAVE_DIR, BACKUP_DIR, GAME_NAME, 
                  MAX_BACKUPS, BACKUP_INTERVAL, COMPRESS_LEVEL),
            daemon=True
        )
        scheduler_thread.start()
        
        # Create first backup immediately on startup
        print("="*60)
        print("🚀 Creating initial backup on startup")
        print("="*60)
        create_backup(SAVE_DIR, BACKUP_DIR, GAME_NAME, MAX_BACKUPS, COMPRESS_LEVEL)
        
        # Main loop - wait for completion or interruption
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Program terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Critical error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()