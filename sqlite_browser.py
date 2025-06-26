#!/usr/bin/env python3
"""
Lightweight curses-based SQLite database browser for viewing, editing, and deleting records.

Author: Yahor Zaleski
License: MIT
Repository: https://github.com/zebrig/sqlite_browser.git

Usage:
    python3 sqlite_browser.py [path/to/database.db]
or
    sqlite_browser.py [path/to/database.db]

Controls:
  In table list:
    Up/Down  - navigate tables
    Enter    - select/enter table
    v        - toggle column/inline view
    i        - view schema for selected table
    s        - execute arbitrary SQL query
    q        - quit

  In record view:
    Up/Down  - navigate records
    e        - edit selected record (opens $EDITOR or vi)
    d        - delete selected record
    r        - reload records
    i        - view table schema
    w        - toggle wrap long rows
    s        - execute arbitrary SQL query
    b or q   - back to table list
"""
import curses
import json
import os
import sqlite3
import re
import subprocess
import shutil
import sys
import tempfile
import textwrap


def main(stdscr, db_path):
    conn = sqlite3.connect(db_path)
    # allow non-UTF-8 text by replacing invalid bytes, so viewer doesn't crash on malformed data
    conn.text_factory = lambda b: b.decode('utf-8', 'replace')
    conn.row_factory = sqlite3.Row
    curses.curs_set(0)
    # reduce ESC key delay so ESC returns promptly in schema view
    if hasattr(curses, 'set_escdelay'):
        try:
            curses.set_escdelay(25)
        except Exception:
            pass
    while True:
        table = table_menu(stdscr, conn)
        if table is None:
            break
        view_table(stdscr, conn, table)


def table_menu(stdscr, conn):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row['name'] for row in cursor]
    if not tables:
        return None
    # pre-fetch record counts and approximate table sizes (requires dbstat virtual table)
    counts = {}
    sizes = {}
    use_dbstat = True
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS dbstat USING dbstat")
    except sqlite3.OperationalError:
        use_dbstat = False
    for t in tables:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
        except sqlite3.DatabaseError:
            cnt = None
        counts[t] = cnt
        if use_dbstat:
            try:
                s = conn.execute("SELECT SUM(pgsize) FROM dbstat WHERE name = ?", (t,)).fetchone()[0]
            except sqlite3.DatabaseError:
                s = None
            sizes[t] = s
        else:
            sizes[t] = None
    idx = 0
    # toggle between inline list view and 3-column view (default to column)
    column_view = True
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "Tables:")
        if not column_view:
            # list view: one table per line (name + counts/sizes inline)
            for i, name in enumerate(tables):
                y = i + 1
                if y >= h - 1:
                    break
                attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
                info = name
                cnt = counts.get(name)
                if cnt is not None:
                    info += f" ({cnt} rows"
                    size = sizes.get(name)
                    if size is not None:
                        if size >= 1024*1024:
                            info += f", {size/1024/1024:.1f}MB"
                        elif size >= 1024:
                            info += f", {size/1024:.1f}KB"
                        else:
                            info += f", {size}B"
                    info += ")"
                stdscr.addstr(y, 2, info[:w-4], attr)
        else:
            # column view: table Name | Rows | Size
            # prepare per-table values
            rows_vals = [str(counts.get(t) or 0) for t in tables]
            size_vals = []
            for t in tables:
                sz = sizes.get(t)
                if sz is None:
                    size_vals.append('')
                elif sz >= 1024*1024:
                    size_vals.append(f"{sz/1024/1024:.1f}MB")
                elif sz >= 1024:
                    size_vals.append(f"{sz/1024:.1f}KB")
                else:
                    size_vals.append(f"{sz}B")
            # compute column widths
            col1 = max((len(n) for n in tables), default=4)
            col2 = max((len(v) for v in rows_vals), default=4)
            col3 = max((len(v) for v in size_vals), default=4)
            # header
            hdr = f"{'Name':{col1}}  {'Rows':>{col2}}  {'Size':>{col3}}"
            stdscr.addstr(1, 2, hdr[:w-4], curses.A_UNDERLINE)
            # rows
            for i, name in enumerate(tables):
                y = i + 2
                if y >= h - 1:
                    break
                attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
                line = f"{name:{col1}}  {rows_vals[i]:>{col2}}  {size_vals[i]:>{col3}}"
                stdscr.addstr(y, 2, line[:w-4], attr)
        help_str = "Up/Down: Navigate  Enter: Select  v: Toggle view  i: Schema  s: SQL query  q: Quit"
        try:
            stdscr.addstr(h-1, 0, help_str[:w])
        except curses.error:
            pass
        stdscr.refresh()
        key = stdscr.getch()
        if key in (ord('i'),):
            view_schema(stdscr, conn, tables[idx])
        if key == ord('s'):
            run_sql(stdscr, conn)
        if key in (curses.KEY_DOWN, ord('j')):
            idx = min(idx+1, len(tables)-1)
        elif key in (curses.KEY_UP, ord('k')):
            idx = max(idx-1, 0)
        elif key in (ord('q'), 27):
            return None
        elif key == ord('v'):
            column_view = not column_view
        elif key in (curses.KEY_ENTER, 10, 13):
            return tables[idx]


def view_table(stdscr, conn, table):
    def load_rows():
        data = conn.execute(f"SELECT rowid AS __rowid__, * FROM '{table}'").fetchall()
        if data:
            cols = data[0].keys()[1:]
        else:
            cols = [col[1] for col in conn.execute(f"PRAGMA table_info('{table}')")]
        rowids = [row['__rowid__'] for row in data]
        rows = [tuple(row)[1:] for row in data]
        return cols, rows, rowids

    cols, rows, rowids = load_rows()
    idx = 0
    start = 0  # track which row to start display from
    wrap = False
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        title = f"Table: {table} ({len(rows)} rows)"
        stdscr.addstr(0, 0, title[:w])
        hdr = ' | '.join(cols)
        # Header (wrap column names when wrapping enabled)
        header_lines = textwrap.wrap(hdr, w) if wrap else [hdr]
        for i, hline in enumerate(header_lines):
            stdscr.addstr(1 + i, 0, hline[:w], curses.A_UNDERLINE)
        # Rows
        if not wrap:
            visible = h - 3 - len(header_lines)
            for i in range(visible):
                ridx = start + i
                if ridx >= len(rows):
                    break
                row = rows[ridx]
                line = ' | '.join(str(x) for x in row)
                attr = curses.A_REVERSE if ridx == idx else curses.A_NORMAL
                stdscr.addstr(1 + len(header_lines) + i, 0, line[:w], attr)
        else:
            # wrap mode: display rows starting at 'start', wrapping long lines
            y = 1 + len(header_lines)
            for ridx in range(start, len(rows)):
                if y >= h-1:
                    break
                row = rows[ridx]
                line = ' | '.join(str(x) for x in row)
                wrapped = textwrap.wrap(line, w)
                for part in wrapped:
                    if y >= h-1:
                        break
                    attr = curses.A_REVERSE if ridx == idx else curses.A_NORMAL
                    stdscr.addstr(y, 0, part, attr)
                    y += 1
        help_str = "Up/Down: Navigate  e: Edit  d: Delete  r: Reload  i: Schema  w: Wrap  s: SQL  b/q: Back"
        try:
            stdscr.addstr(h-1, 0, help_str[:w])
        except curses.error:
            pass
        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_DOWN, ord('j')):
            if idx < len(rows) - 1:
                idx += 1
        elif key in (curses.KEY_UP, ord('k')):
            if idx > 0:
                idx -= 1
        elif key == ord('r'):
            cols, rows, rowids = load_rows()
            idx = start = 0
            continue
        elif key in (ord('b'), ord('q'), 27):
            break
        elif key == ord('i'):
            view_schema(stdscr, conn, table)
            cols, rows, rowids = load_rows()
            continue
        elif key == ord('w'):
            wrap = not wrap
            continue
        elif key == ord('s'):
            run_sql(stdscr, conn)
            cols, rows, rowids = load_rows()
            idx = start = 0
            continue
        elif key == ord('d') and rows:
            if confirm(stdscr, f"Delete row {idx+1}/{len(rows)}? (y/N)"):
                conn.execute(f"DELETE FROM '{table}' WHERE rowid=?", (rowids[idx],))
                conn.commit()
                cols, rows, rowids = load_rows()
                idx = start = 0
            continue
        elif key == ord('e') and rows:
            edit_row(conn, table, cols, rows[idx], rowids[idx])
            cols, rows, rowids = load_rows()
            continue

        # adjust scroll window: in wrap mode, jump to selected row; else scroll by rows
        visible = h - 4
        if wrap:
            # show selected row at top when wrapping
            start = idx
        else:
            if idx < start:
                start = idx
            elif idx >= start + visible:
                start = idx - visible + 1


def confirm(stdscr, message):
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h-2, 0, message[:w])
    stdscr.clrtoeol()
    stdscr.refresh()
    key = stdscr.getch()
    return key in (ord('y'), ord('Y'))

def view_schema(stdscr, conn, table):
    h, w = stdscr.getmaxyx()
    encoding = conn.execute("PRAGMA encoding").fetchone()[0]
    try:
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()[0] or ''
    except Exception:
        ddl = ''
    try:
        cols_info = conn.execute(f"PRAGMA table_xinfo('{table}')").fetchall()
        hidden_col = True
    except sqlite3.DatabaseError:
        cols_info = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        hidden_col = False
    headers = ['Name', 'Type', 'Limit', 'Not Null', 'Default', 'PK']
    if hidden_col:
        headers.append('Hidden')
    rows = []
    rows.append((f"Schema: {table} (encoding: {encoding})", curses.A_BOLD))
    rows.append(("", 0))
    # Pretty-print CREATE TABLE DDL
    m = re.match(r'^(CREATE TABLE.*?\()(.*)(\).*)$', ddl, flags=re.IGNORECASE|re.DOTALL)
    if m:
        pre, body, post = m.group(1), m.group(2), m.group(3)
        rows.append((pre, 0))
        parts, buf, depth = [], [], 0
        for ch in body:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if ch == ',' and depth == 0:
                parts.append(''.join(buf)); buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append(''.join(buf))
        for i, part in enumerate(parts):
            chunk = part.strip() + (',' if i < len(parts)-1 else '')
            for wline in textwrap.wrap(chunk, w-4):
                rows.append(('    ' + wline, 0))
        rows.append((post, 0))
    else:
        for line in textwrap.wrap(ddl, w):
            rows.append((line, 0))
    rows.append(("", 0))
    col_widths = [len(h) for h in headers]
    data = []
    for ci in cols_info:
        name = ci['name']
        typ = ci['type'] or ''
        m = re.search(r"\((\d+)\)", typ)
        limit = m.group(1) if m else ''
        notnull = 'YES' if ci['notnull'] else 'NO'
        default = ci['dflt_value'] or ''
        pk = str(ci['pk']) if ci['pk'] else ''
        hidden = 'YES' if hidden_col and ci['hidden'] else ''
        row = [name, typ, limit, notnull, default, pk]
        if hidden_col:
            row.append(hidden)
        data.append(row)
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    hdr_line = '  '.join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    rows.append((hdr_line, curses.A_UNDERLINE))
    for rec in data:
        line = '  '.join(str(rec[i]).ljust(col_widths[i]) for i in range(len(rec)))
        rows.append((line, 0))
    rows.append(("", 0))
    rows.append(("Indices:", curses.A_UNDERLINE))
    for info in conn.execute(f"PRAGMA index_list('{table}')"):
        name = info['name']; uniq = 'YES' if info['unique'] else 'NO'
        cols = [r['name'] for r in conn.execute(f"PRAGMA index_info('{name}')")]
        text = f"{name} (unique: {uniq}) columns: {', '.join(cols)}"
        for part in textwrap.wrap(text, w-2):
            rows.append((f"  {part}", 0))
    rows.append(("", 0))
    rows.append(("Foreign keys:", curses.A_UNDERLINE))
    for fk in conn.execute(f"PRAGMA foreign_key_list('{table}')"):
        txt = (f"{fk['table']}({fk['to']}) <- {fk['from']} "
               f"on_update={fk['on_update']} on_delete={fk['on_delete']}")
        for part in textwrap.wrap(txt, w-2):
            rows.append((f"  {part}", 0))
    rows.append(("", 0))
    cnt = conn.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
    sz = None
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS dbstat USING dbstat")
        sz = conn.execute("SELECT SUM(pgsize) FROM dbstat WHERE name=?", (table,)).fetchone()[0]
    except sqlite3.DatabaseError:
        pass
    stat = f"Rows: {cnt}"
    if sz is not None:
        if sz >= 1024*1024:
            stat += f", Size: {sz/1024/1024:.1f}MB"
        elif sz >= 1024:
            stat += f", Size: {sz/1024:.1f}KB"
        else:
            stat += f", Size: {sz}B"
    rows.append((stat, 0))
    rows.append(("", 0))
    rows.append(("Triggers:", curses.A_UNDERLINE))
    for trig in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)):
        ln = f"{trig['name']}: {trig['sql'] or ''}"
        for part in textwrap.wrap(ln, w-2):
            rows.append((f"  {part}", 0))

    h, w = stdscr.getmaxyx()
    pad = curses.newpad(len(rows)+1, w)
    for i, (text, attr) in enumerate(rows):
        try:
            pad.addnstr(i, 0, text, w-1, attr)
        except curses.error:
            pass
    pos = 0
    while True:
        pad.refresh(pos, 0, 0, 0, h-2, w-1)
        footer = "Up/Down: Scroll  b/q/ESC: Back"
        try:
            stdscr.addnstr(h-1, 0, footer, w-1, curses.A_DIM)
        except curses.error:
            pass
        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_DOWN, ord('j')) and pos < len(rows) - (h-1):
            pos += 1
        elif key in (curses.KEY_UP, ord('k')) and pos > 0:
            pos -= 1
        elif key in (ord('b'), ord('q'), 27):
            break


def edit_row(conn, table, cols, row, rowid):
    data = {col: row[i] for i, col in enumerate(cols)}
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.json') as tf:
        tf.write(json.dumps(data, indent=2, ensure_ascii=False))
        tf.flush()

        # Suspend curses before calling external editor
        curses.endwin()

        editor = os.environ.get('EDITOR', 'vi')
        subprocess.call([editor, tf.name])

        # Resume curses after editing
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        curses.curs_set(0)
        curses.flushinp()  # Flush any editor leftovers

        tf.seek(0)
        try:
            newdata = json.load(tf)
        except Exception:
            return
    os.unlink(tf.name)
    keys = [k for k in cols if k in newdata]
    vals = [newdata[k] for k in keys]
    set_clause = ', '.join(f"{k}=?" for k in keys)
    sql = f"UPDATE '{table}' SET {set_clause} WHERE rowid=?"
    conn.execute(sql, vals + [rowid])
    conn.commit()


def run_sql(stdscr, conn):
    """
    Prompt for and execute an arbitrary SQL query, printing results or errors,
    then resume the curses UI.
    """
    curses.endwin()
    try:
        sql = input("SQL> ")
    except EOFError:
        sql = ''
    if sql.strip():
        try:
            cur = conn.execute(sql)
            conn.commit()
            if cur.description:
                cols = [d[0] for d in cur.description]
                print(" | ".join(cols))
                rows = cur.fetchall()
                for row in rows:
                    print(" | ".join(str(x) for x in row))
                print(f"{len(rows)} row(s) returned")
            else:
                print("Query executed successfully.")
        except sqlite3.DatabaseError as e:
            print(f"SQL error: {e}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
    else:
        print("No SQL entered.")
    input("Press Enter to continue...")
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(0)
    curses.flushinp()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        db = sys.argv[1]
    else:
        script_dir = os.path.abspath(os.path.dirname(__file__))
        if not shutil.which('php'):
            print("Error: php CLI is required to autodetect database file", file=sys.stderr)
            sys.exit(1)
        try:
            db = subprocess.check_output(
                ['php', '-r', "require 'config.php'; echo DB_FILE;"],
                cwd=script_dir
            ).decode().strip()
        except subprocess.CalledProcessError:
            print("Error: failed to load DB_FILE from config.php", file=sys.stderr)
            sys.exit(1)

    if not os.path.exists(db):
        print(f"Database file not found: {db}", file=sys.stderr)
        sys.exit(1)

    curses.wrapper(main, db)
