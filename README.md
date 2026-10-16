# Library Management System

A complete beginner-friendly Library Management System built with:

- Frontend: HTML5, CSS3, JavaScript
- Backend: Python + Flask
- Database: SQLite
- UI: Responsive dashboard

## Features

1. Admin/Librarian login
2. Dashboard statistics
3. Book management
   - Add
   - Edit
   - Delete
   - Search
   - Available-copy tracking
4. Member management
   - Add
   - Edit
   - Delete
   - Search
5. Issue books
6. Return books
7. Due-date tracking
8. Overdue report
9. Category report
10. Most-issued books report
11. Responsive sidebar navigation
12. SQLite database auto-created on first run
13. Demo data included

## Login

Username: `admin`
Password: `admin123`

## Windows setup

Open PowerShell/CMD inside this project folder:

```text
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open:

http://127.0.0.1:5000

## If `python` is not recognized

Try:

```text
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

## Project structure

```text
library_management_system/
│
├── app.py
├── requirements.txt
├── README.md
├── library.db              # created automatically
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── books.html
│   ├── book_form.html
│   ├── members.html
│   ├── member_form.html
│   ├── issue.html
│   ├── loans.html
│   └── reports.html
│
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

For production, replace the demo password storage with password hashing and add CSRF protection.
