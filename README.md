# Cursor Chat Viewer

A simple GUI application to view and export your Cursor AI chat history.

## Features

- Browse and view all your Cursor chat history
- Search through chats by content or ID
- View chats in raw JSON format or as readable conversation
- Export chats as JSON or formatted text
- Analyze database to find all key prefixes
- Flexible key prefix selection to support different Cursor versions
- Auto-loads your chat database on startup

## Requirements

- Python 3.6+
- Tkinter (usually comes with Python)

## Installation

No installation required. Just download the script and run it:

```bash
python cursor_chat_viewer.py
```

## Usage

1. The application will automatically try to load chats from the default database location: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
2. If your database is in a different location, use the "Browse" button to locate it
3. By default, the application searches for keys with the prefix `composerData:`. If you don't see any records:
   - Use the "Analyze DB" button to see what key prefixes exist in your database
   - Select a different prefix from the dropdown or use the results of the analysis
4. Click on any chat in the left panel to view its content
5. Use the search box to find specific chats
6. Use the "Format as Chat" button to view the chat in a readable conversation format
7. Export chats as JSON or text using the corresponding buttons

## How It Works

Cursor saves chat history in a SQLite database. This tool:
1. Connects to that database
2. Extracts records from the `cursorDiskKV` table matching the selected key prefix
3. Decompresses and decodes the BLOB data
4. Presents it in a readable format

## Troubleshooting

If you don't see any chats:
- Make sure the database path is correct
- Try closing Cursor before running this tool
- Use the "Analyze DB" button to see what key prefixes are used in your database
- Try a different key prefix (different Cursor versions may use different prefixes)
- Check if you have permissions to read the database file

## License

MIT 