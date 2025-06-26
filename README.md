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
    git clone https://github.com/zebrig/sqlite_browser.git
    cd sqlite_browser
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

Create a `config.php` file (see `config.php.example`) in the script's directory:
```php
<?php
// config.php
define('DB_FILE', '/path/to/your/database.db');
// or relative to config.php:
// define('DB_FILE', 'data/my_app.sqlite');
?>
```

and then

```bash
python3 db_browser.py
```

## "Screenshots"

### Tables view
```
Tables:
  Name               Rows     Size
  auth_sessions       15   12.0KB
  change_log          51    4.0KB
  companies            4   12.0KB
  contract_files       2    4.0KB
  contracts            1    4.0KB
  currencies           3    4.0KB
  customer_prefixes   34    4.0KB
  customers            7   60.0KB
  dbstat             133
  invoices            85  312.0KB
  payments           140   32.0KB
  services             7    4.0KB
  sqlite_sequence     11    4.0KB
  user_customers       5    4.0KB
  users                3    4.0KB

Up/Down: Navigate  Enter: Select  v: Toggle view  i: Schema  w: Wrap  s: SQL  q: Quit
```

### Schema view
```
Schema: customer_prefixes (encoding: UTF-8)
CREATE TABLE customer_prefixes (         id INTEGER PRIMARY KEY AUTOINCREMENT,
customer_id INTEGER NOT NULL,         entity TEXT NOT NULL,         property TEXT NOT
NULL,         prefix TEXT NOT NULL,         FOREIGN KEY(customer_id) REFERENCES
customers(id)     )

Name         Type     Limit  Not Null  Default  PK  Hidden
id           INTEGER         NO                 1   NO
customer_id  INTEGER         YES                    NO
entity       TEXT            YES                    NO
property     TEXT            YES                    NO
prefix       TEXT            YES                    NO

Indices:

Foreign keys:
  customers(id) <- customer_id on_update=NO ACTION on_delete=NO ACTION

Rows: 34, Size: 4.0KB
Triggers:

Press any key to return
```

### Table entries view
```
Table: auth_sessions (15 rows)
id | token | user_id | created_at | created_ip | created_user_agent | last_used_at | last_
2 | 717e70b973909a5a215e6d6ff1b22e096138093a85145f685d38311f4bb2b53f | 1 | 2025-06-02 18:0
5 | 72a99e2e4777ee69b43908c02f48d31af4b3dd129d2c57b735a27f5fdcd2e674 | 3 | 2025-06-02 20:0
7 | caa48e1bc7f935c63bce03a7ff4f2994b314cac90fa0d97df617aa5085e4eb9c | 1 | 2025-06-02 21:4
8 | 7630d10c02233cd5b6215eb62eb04362f5b195fdf265e2641e0ab367095a989e | 1 | 2025-06-05 06:1
13 | 7b093be0759d5ec7177723b952ddfb2fb289411393b44d998de5ff84ce7e35e2 | 1 | 2025-06-06 08:
14 | 18eb110fa019f3cf4777ee69b8dfd1a18fcabc6746716205da9b526851b4eee3 | 1 | 2025-06-08 21:
16 | a775a6f30410e6ecfffb1dfd17724ec1b2e573b184f4d29f06673887b989bb46 | 3 | 2025-06-09 10:
17 | 22da373e45e62bd879dd9b1f2a1e0e35bbe28c536f1454c734777183491a5650 | 1 | 2025-06-09 11:
18 | 992687b933995d72aa4dd31efea050b9eb37481699123ab9ba44e4e0db372aa4 | 1 | 2025-06-09 13:
19 | 8e62083f2015e5a4335519a1dc578594be44e0c261e6ee00703fcd279e2f164b | 1 | 2025-06-11 06:
20 | 06afbdc496a8c13a9c857666c10652a873d5b373887592ebb572dbaa176e5749 | 3 | 2025-06-11 15:
21 | c2a1ebe4e6c91cf3d3f5954e9b1a37fc701d9481aec622f8109ae2912ca64430 | 3 | 2025-06-11 17:
22 | 3158abfca64861d54e27a095803ba297c8ef096f3e4edfeada838e554fe8fa0a | 1 | 2025-06-11 18:
23 | 24ee74919332ca0a31e1397e96ec8ba35af0eaf04107ae068d194a414f3eff21 | 1 | 2025-06-16 11:
24 | 34a24a456fc8835063e4d8e275315ce6d0e9b9d753ff806b120abfae48e70257 | 1 | 2025-06-17 12:

Up/Down: Navigate  e: Edit  d: Delete  r: Reload  i: Schema  w: Wrap  s: SQL  b/q: Back
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.
