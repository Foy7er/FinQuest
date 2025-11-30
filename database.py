import sqlite3
import datetime

DB_NAME = "finquest.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            character_name TEXT,
            character_class TEXT,
            level INTEGER DEFAULT 1,
            wallet_balance INTEGER DEFAULT 0,
            savings_balance INTEGER DEFAULT 0,
            savings_start_date TEXT,
            age INTEGER DEFAULT 10
        )
    ''')
    
    # Simple migration for existing databases
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 10')
    except sqlite3.OperationalError:
        pass # Column likely already exists

    # Market Items Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            current_price INTEGER NOT NULL,
            price_history TEXT -- JSON string or comma separated values
        )
    ''')

    # Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (item_id) REFERENCES market_items (id)
        )
    ''')

    # Purchased Games Table (for shop)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchased_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            purchase_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, game_id)
        )
    ''')

    # Seed initial market items if empty
    cursor.execute('SELECT count(*) FROM market_items')
    if cursor.fetchone()[0] == 0:
        initial_items = [
            ('Rare Card', 'A shiny rare collectible card', 100),
            ('Vintage Toy', 'A classic toy from the 90s', 250),
            ('Digital Art', 'A unique piece of digital art', 500),
            ('Logic Pack', 'Unlock 50 new logic puzzles', 1000)
        ]
        cursor.executemany('INSERT INTO market_items (name, description, current_price) VALUES (?, ?, ?)', initial_items)

    conn.commit()
    conn.close()

def add_user(telegram_id, username, character_name, character_class, age):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, username, character_name, character_class, age)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, username, character_name, character_class, age))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_balance(telegram_id, amount, is_savings=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    field = "savings_balance" if is_savings else "wallet_balance"
    cursor.execute(f'UPDATE users SET {field} = {field} + ? WHERE telegram_id = ?', (amount, telegram_id))
    conn.commit()
    conn.commit()
    conn.close()

def delete_user(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
    cursor.execute('DELETE FROM inventory WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)', (telegram_id,))
    conn.commit()
    conn.close()

def add_to_inventory(user_id, item_id, quantity=1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if item already exists in inventory
    cursor.execute('SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?', (user_id, item_id))
    result = cursor.fetchone()
    
    if result:
        new_quantity = result[0] + quantity
        cursor.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?', (new_quantity, user_id, item_id))
    else:
        cursor.execute('INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)', (user_id, item_id, quantity))
        
    conn.commit()
    conn.close()

def get_inventory(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.name, m.description, i.quantity 
        FROM inventory i
        JOIN market_items m ON i.item_id = m.id
        WHERE i.user_id = ?
    ''', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def purchase_game(user_id, game_id):
    """Purchase a game for a user"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO purchased_games (user_id, game_id, purchase_date) VALUES (?, ?, ?)',
                      (user_id, game_id, datetime.datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Already purchased
    finally:
        conn.close()

def get_purchased_games(user_id):
    """Get list of game IDs that user has purchased"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT game_id FROM purchased_games WHERE user_id = ?', (user_id,))
    games = [row[0] for row in cursor.fetchall()]
    conn.close()
    return games
