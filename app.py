from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import uuid

app = Flask(__name__, static_folder='uploads')
CORS(app, origins=["https://oceanbooks.vercel.app", "http://localhost:5000"])

# --------------------------
# Database Connection Helper
# --------------------------
def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------
# ✅ Home Route (Fixed)
# --------------------------
@app.route('/')
def home():
    return jsonify({"message": "OceanBooks API is running!"})


# --------------------------
# Get All Books
# --------------------------
@app.route('/api/books', methods=['GET'])
def get_books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books').fetchall()
    conn.close()

    return jsonify([dict(book) for book in books])


# --------------------------
# Get Single Book by ID
# --------------------------
@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()

    if book is None:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(dict(book))


# --------------------------
# Upload New Book
# --------------------------
@app.route('/api/books', methods=['POST'])
def upload_book():
    title = request.form.get('title')
    author = request.form.get('author')
    category = request.form.get('category')
    description = request.form.get('description')
    book_file = request.files.get('book_file')
    thumbnail = request.files.get('thumbnail')

    if not title or not author or not category or not book_file or not thumbnail:
        return jsonify({"error": "Missing required fields"}), 400

    os.makedirs('uploads/books', exist_ok=True)
    os.makedirs('uploads/thumbnails', exist_ok=True)

    book_filename = f"{uuid.uuid4().hex}_{book_file.filename}"
    thumb_filename = f"{uuid.uuid4().hex}_{thumbnail.filename}"

    book_path = os.path.join('uploads/books', book_filename)
    thumb_path = os.path.join('uploads/thumbnails', thumb_filename)
    book_file.save(book_path)
    thumbnail.save(thumb_path)

    conn = get_db_connection()
    conn.execute('INSERT INTO books (title, author, category, description, file_path, thumbnail_path, downloads, upload_date) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                 (title, author, category, description, book_path, thumb_path, 0))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Book uploaded successfully"})


# --------------------------
# Download Book
# --------------------------
@app.route('/api/books/<int:book_id>/download', methods=['GET'])
def download_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()

    if not book:
        return jsonify({"error": "Book not found"}), 404

    conn = get_db_connection()
    conn.execute('UPDATE books SET downloads = downloads + 1 WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()

    return send_file(book['file_path'], as_attachment=True)


# --------------------------
# Update Book Info
# --------------------------
@app.route('/api/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    title = data.get('title')
    author = data.get('author')
    category = data.get('category')

    conn = get_db_connection()
    conn.execute('UPDATE books SET title = ?, author = ?, category = ? WHERE id = ?',
                 (title, author, category, book_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})


# --------------------------
# Delete Book
# --------------------------
@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})


# --------------------------
# Admin Stats
# --------------------------
@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    conn = get_db_connection()
    total_books = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    total_downloads = conn.execute('SELECT SUM(downloads) FROM books').fetchone()[0] or 0
    total_size = 0
    for book in conn.execute('SELECT file_path FROM books').fetchall():
        if os.path.exists(book['file_path']):
            total_size += os.path.getsize(book['file_path'])
    conn.close()
    total_size_mb = round(total_size / (1024 * 1024), 2)
    return jsonify({
        "total_books": total_books,
        "total_downloads": total_downloads,
        "total_size": f"{total_size_mb} MB"
    })


# --------------------------
# ✅ Admin Login Route
# --------------------------
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    conn = get_db_connection()
    admin = conn.execute(
        'SELECT * FROM admin WHERE username = ? AND password_hash = ?',
        (username, password)
    ).fetchone()
    conn.close()

    if admin:
        return jsonify({"success": True, "message": "Login successful!"})
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# --------------------------
# Serve Uploaded Files
# --------------------------
@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(app.static_folder, filename)


# --------------------------
# Run App
# --------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
