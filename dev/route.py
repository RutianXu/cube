from flask import Flask, render_template, request, session
import sqlite3
from base64 import b64encode
from secrets import token_hex

app = Flask(__name__)
app.config['SECRET_KEY'] = token_hex(32)


# homepage route
@app.route('/')
def homepage():
    return render_template('home.html')


# algorithm route
@app.route('/algorithms/<algorithm_set>', methods=['GET', 'POST'])
def algorithm(algorithm_set):
    sorting_way = 'id'
    if request.method == 'POST':
        if 'sorting-select' in request.form:
            sorting_way = request.form.get('sorting-select')
        # form submission for rating
        if 'rating' in request.form:
            algorithm_id = request.form.get('algorithm_id')
            user_id = session.get('user_id')
            rating = request.form.get('rating')

            # insert the rating into the database
            conn = sqlite3.connect('cube.db')
            cur = conn.cursor()
            cur.execute('SELECT * FROM ratings WHERE algorithm_id = ? AND user_id = ?', (algorithm_id, user_id))  # fetch an existing rating from the database
            if not cur.fetchall():  # check if a rating exists in the database
                # insert rating if a rating is not exist in the database
                cur.execute('INSERT INTO ratings (algorithm_id, user_id, rating) VALUES (?, ?, ?)', (algorithm_id, user_id, rating))
            else:
                # update rating if a rating exist in the database
                cur.execute('UPDATE ratings SET rating = ? WHERE user_id = ? AND algorithm_id = ?', (rating, user_id, algorithm_id))
            conn.commit()
            conn.close()

    # fetch algorithms from the database
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    if sorting_way == 'name':
        # fetch algorithms from the database and order by algorithm name
        cur.execute('SELECT * FROM algorithms WHERE algorithm_set=? ORDER BY name', (algorithm_set,))
    else:
        # fetch algorithms from the database and order by algorithm id
        cur.execute('SELECT * FROM algorithms WHERE algorithm_set=? ORDER BY id', (algorithm_set,))
    algorithms = cur.fetchall()
    conn.close()
    # process algorithms for display in the website
    algorithms = [list(item) for item in algorithms]  # store algorithms in a list
    alg = []  # list for storing algorithms in a list with images
    algs = []  # list for storing other algorithms in a list without images
    for algorithm in algorithms:
        image_blob = algorithm[-1]
        # change image value from blob to a base64 string
        if image_blob:
            encoded_image = b64encode(image_blob).decode('utf-8')
            algorithm[-1] = encoded_image
            alg.append(algorithm)
        else:
            algs.append(algorithm)

    # fetch ratings from the database
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute('SELECT algorithm_id, ROUND(AVG(rating), 1) AS average_rating, COUNT(rating) AS num_ratings FROM ratings GROUP BY algorithm_id')
    ratings = cur.fetchall()
    conn.close()
    ratings = {item[0]: item[1] for item in ratings}

    return render_template('algorithms.html', alg=alg, algs=algs, ratings=ratings, algorithm_set=algorithm_set, sorting_way=sorting_way)


# registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    username_exist = False  # flag for checking if username exist in the database
    registered = False  # flag for checking if user registered successfully

    if request.method == 'POST':
        # get the username and password from the form
        username = request.form.get('username')
        password = request.form.get('password')

        # check if the account exist in the database
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=?', (username,))  # fetch accounts with the same username
        check_username = cur.fetchall()
        if not check_username:
            # insert the new user into the database
            cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            registered = True
        else:
            # tell the user to use a different username
            username_exist = True
        conn.close()

    return render_template('register.html', username_exist=username_exist, registered=registered)


# login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    logged_in = False  # flag for checking if user is logged in for direct them to homepage
    wrong_details = False  # flag for checking if user's username and password is correct

    # form submission for login
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # check if the user exists in the database
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cur.fetchone()
        conn.close()

        # if user exists, to login and set up session variables
        if user:
            logged_in = True
            session['username'] = username
            session['user_id'] = user[0]
        else:
            # tell user if the username or password is wrong
            wrong_details = True
    return render_template('login.html', logged_in=logged_in, wrong_details=wrong_details)


# logout route
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logged_out = False  # flag for checking if user logged out
    delete_account = False # flag for checking if account deleted
    if request.method == 'POST':
        if 'logout' in request.form or 'delete' in request.form:
            if request.form.get('delete') == 'delete':
                # delete user account, ratings, times in the database
                user_id = session.get('user_id')
                conn = sqlite3.connect('cube.db')
                cur = conn.cursor()
                cur.execute('DELETE FROM users WHERE id = ?', (user_id,))
                cur.execute('DELETE FROM ratings WHERE user_id = ?', (user_id,))
                cur.execute('DELETE FROM timer WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                session.pop('username')
                session.pop('user_id')
                delete_account = True
            else:
                # remove session variables
                session.pop('username')
                session.pop('user_id')
                logged_out = True
    return render_template('logout.html', logged_out=logged_out, delete_account=delete_account)


# timer route
@app.route('/timer', methods=['GET', 'POST'])
def timer():
    # if user is not logged in, redirect to login page
    if 'user_id' not in session:
        logged_in = False  # flag for checking if user is logged in
        times = None
    else:
        user_id = session.get('user_id')
        logged_in = True

        if request.method == 'POST':
            # save time in database
            if 'time' in request.form:
                time_value = request.form.get('time')
                conn = sqlite3.connect('cube.db')
                cur = conn.cursor()
                cur.execute('INSERT INTO timer (time, user_id) VALUES (?, ?)', (time_value, user_id))
                conn.commit()
                conn.close()
            # clear times in database
            elif 'clear' in request.form:
                conn = sqlite3.connect('cube.db')
                cur = conn.cursor()
                cur.execute('DELETE FROM timer WHERE user_id=?', (user_id,))
                conn.commit()
                conn.close()

        # fetch times from the database
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('SELECT time FROM timer WHERE user_id=?', (user_id,))
        times = cur.fetchall()
        conn.close()

    return render_template('timer.html', times=times, logged_in=logged_in)


if __name__ == '__main__':
    app.run(debug=True)
