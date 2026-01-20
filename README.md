# BackupManager - automaticaly makes backups and put in selected folder.
Example of Setting.ini:
[Paths]
save_dir = C:\Users\user\AppData\Local\Hinterland (Put path to the saves folder here)
backup_dir = C:\Users\user1\AppData\Local\TLDbackups (Put here where you want make backups. By default, it's saved to document folder to avoid conflicts)

[Backup]
game_name = TLD_2.02 (How your backups files will be named)
max_backups = 50 (When number will 50, deleting old saves)
backup_interval = 20 (Frequency of backups creating (in minutes))
