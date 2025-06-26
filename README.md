# Command-line SQLite DB Browser

A lightweight, terminal-based (curses) SQLite database browser for viewing, editing, and deleting records.

Author: **Yahor Zaleski**
License: **MIT**
Version: 0.1.0

## Features

*   Navigate and view tables in an SQLite database.
*   Two table list view modes: compact list and detailed columns (Name, Rows, Size).
*   View table schema (DDL, columns, indices, foreign keys, triggers).
*   View records within a table.
*   Toggle wrapping for long record lines.
*   Edit records using your system's default editor (`$EDITOR` or `vi`).
*   Delete records (with confirmation).
*   Execute arbitrary SQL queries directly.
*   Automatically detects database file from `config.php` (if present and PHP CLI is installed) or accepts a path as an argument.

## Requirements

*   Python 3.6+
*   `curses` library (standard on Linux/macOS, may require `windows-curses` on Windows, though this script is primarily Unix-oriented).
*   (Optional) `php` CLI: if you want to use the `config.php` feature to auto-detect the database file.
*   (Optional) `readline` Python module: for command history in the SQL prompt.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/zebrig/sqlite-cli-browser.git
    cd sqlite-cli-browser
    chmod 755 sqlite_browser.py
    ```
    
## Usage

Run the script with the path to your SQLite database file:

```bash
python3 sqlite_browser.py /path/to/your/database.db
```

or

```bash
sqlite_browser.py /path/to/your/database.db
```

Or, if you have a `config.php` file in the same directory as the script defining `DB_FILE`, you can run it without arguments (requires PHP CLI to be installed and in your PATH):

```bash
python3 db_browser.py
```

Create a `config.php` file (see `config.php.example`) in the script's directory:
```php
<?php
// config.php
define('DB_FILE', '/path/to/your/database.db');
// or relative to config.php:
// define('DB_FILE', 'data/my_app.sqlite');
?>
```

## Controls

### In Table List:

*   **Up/Down Arrows (or k/j)**: Navigate tables
*   **Enter**: Select/enter table
*   **v**: Toggle column/inline view for table list
*   **i**: View schema for selected table
*   **s**: Execute arbitrary SQL query
*   **q (or Esc)**: Quit

### In Record View:

*   **Up/Down Arrows (or k/j)**: Navigate records
*   **e**: Edit selected record (opens `$EDITOR` or `vi`)
*   **d**: Delete selected record (with confirmation)
*   **r**: Reload records for the current table
*   **i**: View table schema
*   **w**: Toggle wrap for long record rows
*   **s**: Execute arbitrary SQL query
*   **b or q (or Esc)**: Back to table list

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate (if any are added in the future).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
