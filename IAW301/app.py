import sqlite3
import secrets
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

db_name = "iaw301"


def init_db():
    connection = sqlite3.connect(database=db_name)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.executemany("""
        INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)
    """, [
        ("admin", "123"),
        ("user1", "456"),
        ("user2", "password3")
    ])

    connection.commit()
    cursor.close()
    connection.close()


init_db()

app = FastAPI(title="iaw301_webapp")

# Simple in-memory session store: {session_token: username}
SESSIONS = {}


def get_current_user(request: Request):
    """Return the username tied to the request's session cookie, or None."""
    token = request.cookies.get("session_token")
    if token and token in SESSIONS:
        return SESSIONS[token]
    return None


LOGIN_FORM_HTML = """
<html>
    <head>
        <title>Login</title>
    </head>
    <meta charset="UTF-8">
    <body>
        <h1>Login</h1>
        {message}
        <form action="/login" method="post">
            <label for="username">Username/Email:</label>
            <input type="text" id="username" name="username" required><br><br>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required><br><br>
            <input type="submit" value="Login">
        </form>
    </body>
</html>
"""

WELCOME_HTML = """
<html>
    <head>
        <title>Welcome</title>
    </head>
    <meta charset="UTF-8">
    <body>
        <h1>Login successful</h1>
        <p>Welcome, {username}!</p>
        <form action="/logout" method="post">
            <input type="submit" value="Logout">
        </form>
    </body>
</html>
"""


@app.get("/")
def root(request: Request):
    """Redirect to the login form, or to the welcome page if already logged in."""
    username = get_current_user(request)
    if username:
        return HTMLResponse(content=WELCOME_HTML.format(username=username))
    return RedirectResponse(url="/login-form")


@app.get("/login-form")
def get_login_form():
    return HTMLResponse(content=LOGIN_FORM_HTML.format(message=""))


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    connection = sqlite3.connect(database=db_name)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = cursor.fetchone()
    cursor.close()
    connection.close()

    if row is None:
        # Login failed
        html = LOGIN_FORM_HTML.format(
            message="<p style='color:red;'>Login failed: invalid username or password.</p>"
        )
        return HTMLResponse(content=html, status_code=401)

    # Login success: create a session and set it as a cookie
    token = secrets.token_hex(16)
    SESSIONS[token] = username

    response = HTMLResponse(content=WELCOME_HTML.format(username=username))
    response.set_cookie(key="session_token", value=token, httponly=True)
    return response


@app.post("/logout")
def logout(request: Request):
    token = request.cookies.get("session_token")
    if token:
        SESSIONS.pop(token, None)

    response = RedirectResponse(url="/login-form", status_code=302)
    response.delete_cookie("session_token")
    return response


@app.get("/ping")
def ping():
    return "pong"


@app.get("/all")
def get_all_users():
    connection = sqlite3.connect(database=db_name)
    cursor = connection.cursor()
    cursor.execute("SELECT username, password FROM users")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    rows_html = "".join(
        f"<tr><td>{username}</td><td>{password}</td></tr>"
        for username, password in rows
    )
    html = f"""
    <html>
        <head>
            <title>All users</title>
        </head>
        <meta charset="UTF-8">
        <body>
            <h1>All users</h1>
            <table border="1">
                <tr><th>Username/Email</th><th>Password</th></tr>
                {rows_html}
            </table>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    uvicorn.run(app=app, host="127.0.0.1", port=8888)