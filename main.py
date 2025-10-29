from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_cors import CORS
import sqlite3, os, uuid

app = Flask(__name__, static_folder='uploads', template_folder='.')
CORS(app)

# ---- Folder setup ----
UPLOAD_DIR = "uploads"
BOOKS_DIR = os.path.join(UPLOAD_DIR, "books")
THUMBNAILS_DIR = os.path.join(UPLOAD_DIR, "thumbnails")
os.makedirs(BOOKS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

# ---- Database initialization ----
def init_db():
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            thumbnail_name TEXT NOT NULL,
            thumbnail_path TEXT NOT NULL,
            file_size INTEGER,
            downloads INTEGER DEFAULT 0,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # Default admin credentials
    cursor.execute('''
        INSERT OR IGNORE INTO admin (id, username, password_hash)
        VALUES (1, 'admin', 'admin123')
    ''')

    conn.commit()
    conn.close()

init_db()

# ---- Helper functions ----
def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

def format_file_size(size_bytes):
    if not size_bytes: return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names)-1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

# ---- HTML Routes ----
@app.route('/')
def index_page():
    return "✅ Flask Backend Running on Render Successfully!"

# (You can enable your HTML routes later if using templates)
# @app.route('/main')
# def main_page():
#     return render_template('main.html')

# ---- API: Books ----
@app.route('/api/books', methods=['GET'])
def get_books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY upload_date DESC').fetchall()
    conn.close()
    result = []
    for b in books:
        thumb = os.path.basename(b["thumbnail_path"])
        result.append({
            "id": b["id"],
            "title": b["title"],
            "author": b["author"],
            "category": b["category"],
            "description": b["description"],
            "file_name": b["file_name"],
            "file_size": format_file_size(b["file_size"]),
            "downloads": b["downloads"],
            "upload_date": b["upload_date"],
            "thumbnail_path": f"/api/thumbnails/{thumb}"
        })
    return jsonify(result)

@app.route('/api/books', methods=['POST'])
def upload_book():
    allowed_books = ['.pdf', '.epub', '.doc', '.docx']
    allowed_images = ['.jpg', '.jpeg', '.png', '.webp']
    try:
        title = request.form.get('title')
        author = request.form.get('author')
        category = request.form.get('category')
        desc = request.form.get('description', '')
        book_file = request.files.get('book_file')
        thumb = request.files.get('thumbnail')

        if not all([title, author, category, book_file, thumb]):
            return jsonify({"error": "All fields are required"}), 400

        book_ext = os.path.splitext(book_file.filename)[1].lower()
        thumb_ext = os.path.splitext(thumb.filename)[1].lower()

        if book_ext not in allowed_books:
            return jsonify({"error": "Invalid book file"}), 400
        if thumb_ext not in allowed_images:
            return jsonify({"error": "Invalid thumbnail"}), 400

        book_uuid = f"{uuid.uuid4()}{book_ext}"
        thumb_uuid = f"{uuid.uuid4()}{thumb_ext}"
        book_path = os.path.join(BOOKS_DIR, book_uuid)
        thumb_path = os.path.join(THUMBNAILS_DIR, thumb_uuid)

        book_file.save(book_path)
        thumb.save(thumb_path)
        size = os.path.getsize(book_path)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO books (title, author, category, description, file_name, file_path, thumbnail_name, thumbnail_path, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, author, category, desc, book_file.filename, book_path, thumb.filename, thumb_path, size))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Book uploaded successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ For Render — Do not use app.run(), just expose app
app = app