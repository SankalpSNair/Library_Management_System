from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
import uuid


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = " "
    
    # Upload configuration
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Database path in instance folder
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    db_path = os.path.join(app.instance_path, "library.sqlite")

    def get_connection() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_uploaded_file(file):
        if file and allowed_file(file.filename):
            # Generate unique filename
            filename = secure_filename(file.filename)
            name, ext = os.path.splitext(filename)
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            return f"uploads/{unique_filename}"
        return None

    def init_db() -> None:
        with get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    available INTEGER NOT NULL DEFAULT 1,
                    image_path TEXT
                );
                """
            )
            # Add image_path column if it doesn't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE books ADD COLUMN image_path TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
    
    init_db()

    @app.route("/")
    def index():
        with get_connection() as conn:
            rows = conn.execute("SELECT id, title, author, available, image_path FROM books ORDER BY id ASC").fetchall()
            books = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "author": row["author"],
                    "available": bool(row["available"]),
                    "image_path": row["image_path"],
                }
                for row in rows
            ]
            
            # Calculate statistics
            total_books = len(books)
            available_books = sum(1 for book in books if book["available"])
            borrowed_books = total_books - available_books
            
            stats = {
                "total": total_books,
                "available": available_books,
                "borrowed": borrowed_books
            }
            
        return render_template("index.html", books=books, search_results=None, stats=stats)

    @app.post("/add_book")
    def add_book():
        title = (request.form.get("title") or "").strip()
        author = (request.form.get("author") or "").strip()
        image_file = request.files.get('image')

        if not title or not author:
            flash("Fill all required fields to add a book.", "error")
            return redirect(url_for("index"))

        # Handle image upload
        image_path = None
        if image_file and image_file.filename:
            image_path = save_uploaded_file(image_file)
            if not image_path:
                flash("Invalid image file. Please upload a valid image (PNG, JPG, JPEG, GIF, WebP).", "error")
                return redirect(url_for("index"))

        with get_connection() as conn:
            conn.execute(
                "INSERT INTO books (title, author, available, image_path) VALUES (?, ?, 1, ?)",
                (title, author, image_path),
            )
            conn.commit()
        
        success_msg = f"Book '{title}' added!"
        if image_path:
            success_msg += " Image uploaded successfully."
        flash(success_msg, "success")
        return redirect(url_for("index"))

    @app.post("/borrow_book/<int:book_id>")
    def borrow_book(book_id: int):
        with get_connection() as conn:
            row = conn.execute("SELECT id, title, available FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                flash("Book not found.", "error")
                return redirect(url_for("index"))
            if not bool(row["available"]):
                flash(f"Book '{row['title']}' is already borrowed.", "warning")
                return redirect(url_for("index"))
            conn.execute("UPDATE books SET available = 0 WHERE id = ?", (book_id,))
            conn.commit()
            flash(f"Book '{row['title']}' borrowed.", "info")
        return redirect(url_for("index"))

    @app.post("/return_book/<int:book_id>")
    def return_book(book_id: int):
        with get_connection() as conn:
            row = conn.execute("SELECT id, title, available FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                flash("Book not found.", "error")
                return redirect(url_for("index"))
            if bool(row["available"]):
                flash(f"Book '{row['title']}' is already available.", "warning")
                return redirect(url_for("index"))
            conn.execute("UPDATE books SET available = 1 WHERE id = ?", (book_id,))
            conn.commit()
            flash(f"Book '{row['title']}' returned.", "success")
        return redirect(url_for("index"))

    @app.post("/delete_book/<int:book_id>")
    def delete_book(book_id: int):
        with get_connection() as conn:
            row = conn.execute("SELECT id, title, image_path FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                flash("Book not found.", "error")
                return redirect(url_for("index"))
            
            # Delete the book from database
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            
            # Delete associated image file if it exists
            if row["image_path"]:
                try:
                    image_file_path = os.path.join("static", row["image_path"])
                    if os.path.exists(image_file_path):
                        os.remove(image_file_path)
                except Exception as e:
                    # Log error but don't fail the deletion
                    print(f"Error deleting image file: {e}")
            
            flash(f"Book '{row['title']}' deleted successfully.", "success")
        return redirect(url_for("index"))

    @app.post("/check_book")
    def check_book():
        query = (request.form.get("query") or "").strip()
        if not query:
            flash("Enter a title to check.", "error")
            return redirect(url_for("index"))

        with get_connection() as conn:
            # Get all books for the main display
            all_rows = conn.execute("SELECT id, title, author, available, image_path FROM books ORDER BY id ASC").fetchall()
            books = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "author": row["author"],
                    "available": bool(row["available"]),
                    "image_path": row["image_path"],
                }
                for row in all_rows
            ]
            
            # Get search results
            search_rows = conn.execute(
                "SELECT id, title, author, available, image_path FROM books WHERE lower(title) LIKE lower(?)",
                (f"%{query}%",),
            ).fetchall()
            
            if search_rows:
                search_results = [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "author": row["author"],
                        "available": bool(row["available"]),
                        "image_path": row["image_path"],
                    }
                    for row in search_rows
                ]
                
                # Calculate statistics
                total_books = len(books)
                available_books = sum(1 for book in books if book["available"])
                borrowed_books = total_books - available_books
                
                stats = {
                    "total": total_books,
                    "available": available_books,
                    "borrowed": borrowed_books
                }
                
                flash(f"Found {len(search_results)} book(s) containing '{query}'", "info")
                return render_template("index.html", books=books, search_results=search_results, stats=stats)
            else:
                # Calculate statistics
                total_books = len(books)
                available_books = sum(1 for book in books if book["available"])
                borrowed_books = total_books - available_books
                
                stats = {
                    "total": total_books,
                    "available": available_books,
                    "borrowed": borrowed_books
                }
                
                flash("No books found containing those words.", "error")
                return render_template("index.html", books=books, search_results=None, stats=stats)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)



