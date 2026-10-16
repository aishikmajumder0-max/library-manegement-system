from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from functools import wraps
from datetime import datetime, date, timedelta
from pathlib import Path

app = Flask(__name__)
app.secret_key = "library-management-demo-secret-key"
DB = Path(__file__).with_name("library.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Librarian'
    );
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isbn TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        publisher TEXT,
        year INTEGER,
        quantity INTEGER NOT NULL DEFAULT 1,
        available INTEGER NOT NULL DEFAULT 1,
        shelf TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        department TEXT,
        join_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active'
    );
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT,
        status TEXT NOT NULL DEFAULT 'Issued',
        FOREIGN KEY(book_id) REFERENCES books(id),
        FOREIGN KEY(member_id) REFERENCES members(id)
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute("INSERT INTO users(username,password,full_name,role) VALUES(?,?,?,?)",
                     ("admin", "admin123", "Library Administrator", "Administrator"))
    if conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        books = [
            ("9780132350884","Clean Code","Robert C. Martin","Programming","Prentice Hall",2008,5,5,"A-01"),
            ("9780262033848","Introduction to Algorithms","Cormen, Leiserson, Rivest","Computer Science","MIT Press",2009,4,4,"A-02"),
            ("9780131103627","The C Programming Language","Kernighan & Ritchie","Programming","Prentice Hall",1988,3,3,"A-03"),
            ("9780596007126","Head First Python","Paul Barry","Programming","O'Reilly",2010,3,3,"B-01"),
            ("9788131773388","Database System Concepts","Silberschatz","Database","McGraw Hill",2019,4,4,"B-02")
        ]
        conn.executemany("""INSERT INTO books(isbn,title,author,category,publisher,year,quantity,available,shelf)
                            VALUES(?,?,?,?,?,?,?,?,?)""", books)
    if conn.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
        members = [
            ("LIB001","Aishik Student","aishik@example.com","9876543210","CSE","2026-01-10","Active"),
            ("LIB002","Rahul Das","rahul@example.com","9876501234","CSE","2026-02-12","Active"),
            ("LIB003","Priya Sen","priya@example.com","9876512345","ECE","2026-03-05","Active")
        ]
        conn.executemany("""INSERT INTO members(member_id,name,email,phone,department,join_date,status)
                            VALUES(?,?,?,?,?,?,?)""", members)
    conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {"today": date.today().isoformat(), "current_year": datetime.now().year}

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password)).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    stats = {
        "books": conn.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "copies": conn.execute("SELECT COALESCE(SUM(quantity),0) FROM books").fetchone()[0],
        "available": conn.execute("SELECT COALESCE(SUM(available),0) FROM books").fetchone()[0],
        "members": conn.execute("SELECT COUNT(*) FROM members WHERE status='Active'").fetchone()[0],
        "issued": conn.execute("SELECT COUNT(*) FROM loans WHERE status='Issued'").fetchone()[0],
        "overdue": conn.execute("SELECT COUNT(*) FROM loans WHERE status='Issued' AND due_date < ?", (date.today().isoformat(),)).fetchone()[0]
    }
    recent = conn.execute("""SELECT loans.*, books.title, members.name, members.member_id
                             FROM loans JOIN books ON books.id=loans.book_id
                             JOIN members ON members.id=loans.member_id
                             ORDER BY loans.id DESC LIMIT 8""").fetchall()
    conn.close()
    return render_template("dashboard.html", stats=stats, recent=recent)

@app.route("/books")
@login_required
def books():
    q = request.args.get("q","").strip()
    conn = get_db()
    if q:
        rows = conn.execute("""SELECT * FROM books WHERE title LIKE ? OR author LIKE ?
                               OR isbn LIKE ? OR category LIKE ? ORDER BY id DESC""",
                            tuple([f"%{q}%"]*4)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("books.html", books=rows, q=q)

@app.route("/books/add", methods=["GET","POST"])
@login_required
def add_book():
    if request.method == "POST":
        data = request.form
        try:
            quantity = int(data.get("quantity",1))
            conn = get_db()
            conn.execute("""INSERT INTO books(isbn,title,author,category,publisher,year,quantity,available,shelf)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                         (data["isbn"],data["title"],data["author"],data["category"],data.get("publisher"),
                          int(data["year"]) if data.get("year") else None,quantity,quantity,data.get("shelf")))
            conn.commit(); conn.close()
            flash("Book added successfully.", "success")
            return redirect(url_for("books"))
        except Exception as e:
            flash(f"Could not add book: {e}", "danger")
    return render_template("book_form.html", book=None)

@app.route("/books/edit/<int:book_id>", methods=["GET","POST"])
@login_required
def edit_book(book_id):
    conn = get_db()
    book = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book:
        conn.close(); flash("Book not found.", "danger"); return redirect(url_for("books"))
    if request.method == "POST":
        data = request.form
        old_qty = book["quantity"]
        new_qty = int(data.get("quantity",1))
        delta = new_qty - old_qty
        new_available = max(0, book["available"] + delta)
        conn.execute("""UPDATE books SET isbn=?,title=?,author=?,category=?,publisher=?,year=?,
                        quantity=?,available=?,shelf=? WHERE id=?""",
                     (data["isbn"],data["title"],data["author"],data["category"],data.get("publisher"),
                      int(data["year"]) if data.get("year") else None,new_qty,new_available,data.get("shelf"),book_id))
        conn.commit(); conn.close()
        flash("Book updated successfully.", "success")
        return redirect(url_for("books"))
    conn.close()
    return render_template("book_form.html", book=book)

@app.route("/books/delete/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    conn = get_db()
    active = conn.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND status='Issued'", (book_id,)).fetchone()[0]
    if active:
        flash("Cannot delete a book that is currently issued.", "danger")
    else:
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.commit(); flash("Book deleted.", "success")
    conn.close()
    return redirect(url_for("books"))

@app.route("/members")
@login_required
def members():
    q = request.args.get("q","").strip()
    conn = get_db()
    if q:
        rows = conn.execute("""SELECT * FROM members WHERE name LIKE ? OR member_id LIKE ? OR department LIKE ?
                               ORDER BY id DESC""", (f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM members ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("members.html", members=rows, q=q)

@app.route("/members/add", methods=["GET","POST"])
@login_required
def add_member():
    if request.method == "POST":
        d=request.form
        try:
            conn=get_db()
            conn.execute("""INSERT INTO members(member_id,name,email,phone,department,join_date,status)
                            VALUES(?,?,?,?,?,?,?)""",
                         (d["member_id"],d["name"],d.get("email"),d.get("phone"),d.get("department"),
                          d.get("join_date") or date.today().isoformat(),d.get("status","Active")))
            conn.commit(); conn.close(); flash("Member added successfully.","success")
            return redirect(url_for("members"))
        except Exception as e:
            flash(f"Could not add member: {e}","danger")
    return render_template("member_form.html", member=None)

@app.route("/members/edit/<int:member_id>", methods=["GET","POST"])
@login_required
def edit_member(member_id):
    conn=get_db(); member=conn.execute("SELECT * FROM members WHERE id=?",(member_id,)).fetchone()
    if not member:
        conn.close(); flash("Member not found.","danger"); return redirect(url_for("members"))
    if request.method=="POST":
        d=request.form
        conn.execute("""UPDATE members SET member_id=?,name=?,email=?,phone=?,department=?,join_date=?,status=?
                        WHERE id=?""",
                     (d["member_id"],d["name"],d.get("email"),d.get("phone"),d.get("department"),
                      d.get("join_date"),d.get("status","Active"),member_id))
        conn.commit(); conn.close(); flash("Member updated.","success")
        return redirect(url_for("members"))
    conn.close(); return render_template("member_form.html", member=member)

@app.route("/members/delete/<int:member_id>", methods=["POST"])
@login_required
def delete_member(member_id):
    conn=get_db()
    active=conn.execute("SELECT COUNT(*) FROM loans WHERE member_id=? AND status='Issued'",(member_id,)).fetchone()[0]
    if active: flash("Cannot delete a member with active loans.","danger")
    else:
        conn.execute("DELETE FROM members WHERE id=?",(member_id,)); conn.commit(); flash("Member deleted.","success")
    conn.close(); return redirect(url_for("members"))

@app.route("/issue", methods=["GET","POST"])
@login_required
def issue_book():
    conn=get_db()
    if request.method=="POST":
        book_id=int(request.form["book_id"]); member_id=int(request.form["member_id"])
        due=request.form.get("due_date") or (date.today()+timedelta(days=14)).isoformat()
        book=conn.execute("SELECT * FROM books WHERE id=?",(book_id,)).fetchone()
        member=conn.execute("SELECT * FROM members WHERE id=? AND status='Active'",(member_id,)).fetchone()
        if not book or not member: flash("Invalid book or member.","danger")
        elif book["available"] <= 0: flash("No available copy of this book.","danger")
        elif conn.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND member_id=? AND status='Issued'",(book_id,member_id)).fetchone()[0]:
            flash("This member already has this book issued.","danger")
        else:
            conn.execute("""INSERT INTO loans(book_id,member_id,issue_date,due_date,status)
                            VALUES(?,?,?,?, 'Issued')""",(book_id,member_id,date.today().isoformat(),due))
            conn.execute("UPDATE books SET available=available-1 WHERE id=?",(book_id,))
            conn.commit(); flash("Book issued successfully.","success")
            conn.close(); return redirect(url_for("loans"))
    books=conn.execute("SELECT * FROM books WHERE available>0 ORDER BY title").fetchall()
    members=conn.execute("SELECT * FROM members WHERE status='Active' ORDER BY name").fetchall()
    conn.close()
    return render_template("issue.html", books=books, members=members, default_due=(date.today()+timedelta(days=14)).isoformat())

@app.route("/return/<int:loan_id>", methods=["POST"])
@login_required
def return_book(loan_id):
    conn=get_db()
    loan=conn.execute("SELECT * FROM loans WHERE id=? AND status='Issued'",(loan_id,)).fetchone()
    if loan:
        conn.execute("UPDATE loans SET return_date=?,status='Returned' WHERE id=?",(date.today().isoformat(),loan_id))
        conn.execute("UPDATE books SET available=MIN(quantity,available+1) WHERE id=?",(loan["book_id"],))
        conn.commit(); flash("Book returned successfully.","success")
    else: flash("Active loan not found.","danger")
    conn.close(); return redirect(url_for("loans"))

@app.route("/loans")
@login_required
def loans():
    status=request.args.get("status","all")
    conn=get_db()
    base="""SELECT loans.*, books.title, books.isbn, members.name, members.member_id
             FROM loans JOIN books ON books.id=loans.book_id JOIN members ON members.id=loans.member_id"""
    if status in ("Issued","Returned"):
        rows=conn.execute(base+" WHERE loans.status=? ORDER BY loans.id DESC",(status,)).fetchall()
    else:
        rows=conn.execute(base+" ORDER BY loans.id DESC").fetchall()
    conn.close()
    return render_template("loans.html", loans=rows, status=status)

@app.route("/reports")
@login_required
def reports():
    conn=get_db()
    categories=conn.execute("SELECT category,COUNT(*) count,SUM(quantity) copies FROM books GROUP BY category ORDER BY copies DESC").fetchall()
    overdue=conn.execute("""SELECT loans.*,books.title,members.name,members.member_id
                            FROM loans JOIN books ON books.id=loans.book_id JOIN members ON members.id=loans.member_id
                            WHERE loans.status='Issued' AND loans.due_date < ? ORDER BY loans.due_date""",(date.today().isoformat(),)).fetchall()
    top=conn.execute("""SELECT books.title,COUNT(loans.id) times_issued
                        FROM loans JOIN books ON books.id=loans.book_id GROUP BY books.id
                        ORDER BY times_issued DESC LIMIT 10""").fetchall()
    conn.close()
    return render_template("reports.html", categories=categories, overdue=overdue, top=top)

@app.route("/api/stats")
@login_required
def api_stats():
    conn=get_db()
    data={
        "books":conn.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "members":conn.execute("SELECT COUNT(*) FROM members").fetchone()[0],
        "issued":conn.execute("SELECT COUNT(*) FROM loans WHERE status='Issued'").fetchone()[0],
        "available":conn.execute("SELECT COALESCE(SUM(available),0) FROM books").fetchone()[0]
    }
    conn.close()
    return jsonify(data)

init_db()

if __name__=="__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
