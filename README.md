# Library Management System

This is a simple Library Management System web application built with Flask. It allows users to manage books, members, and borrowing records in a library.

## Features
- Add, edit, and delete books
- Manage library members
- Track book borrowing and returns
- Upload and manage book cover images
- Responsive web interface

## Project Structure
```
library_app/
    app.py                # Main Flask application
    instance/
    static/
        script.js         # JavaScript for frontend interactions
        style.css         # CSS styles
        uploads/          # Uploaded book cover images
    templates/
        index.html        # Main HTML template
```

## Getting Started

### Prerequisites
- Python 3.x
- Flask

### Installation
1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd Library_Management
   ```
2. Install dependencies:
   ```sh
   pip install flask
   ```
3. Run the application:
   ```sh
   cd library_app
   python app.py
   ```
4. Open your browser and go to `http://127.0.0.1:5000/`

## Usage
- Use the web interface to add books, manage members, and track borrow/return records.
- Book cover images can be uploaded via the interface.

## License
This project is licensed under the MIT License.
