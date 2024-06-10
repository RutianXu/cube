from flask import Flask, render_template, request, redirect, session
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
    # form submission for rating
    if request.method == 'POST':  
        algorithm_id = request.form['algorithm_id']
        user_id = session.get('user_id')
        rating = request.form['rating']

        # insert the rating into the database
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO ratings (algorithm_id, user_id, rating) VALUES (?, ?, ?)', (algorithm_id, user_id, rating))
        conn.commit()
        conn.close()

    # fetch algorithms from the database
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM algorithms WHERE algorithm_set=?', (algorithm_set,))
    algorithms = cur.fetchall()
    conn.close()

    # process algorithms for display in the website
    algorithms = [list(item) for item in algorithms] # store algroithms in a list
    alg = [] # for storing algorithms in a list with images
    algs = [] # for storing other algorithms in a list without images
    for algorithm in algorithms:
        image_blob = algorithm[-1]
        # change image value from blob to binary to a base64 string 
        if image_blob:
            encoded_image = b64encode(image_blob).decode('utf-8')
            algorithm[-1] = encoded_image
            alg.append(algorithm)
        else:
            algs.append(algorithm)

    return render_template('algorithms.html', alg=alg, algs=algs)


# registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    # form submission for register
    if request.method == 'POST':  
        username = request.form['username']
        password = request.form['password']

        # insert the new user into the database
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return redirect('/login')  

    return render_template('register.html')


# login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    # form submission for login
    if request.method == 'POST':  
        username = request.form['username']
        password = request.form['password']

        # check if the user exists in the database
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cur.fetchone()
        conn.close()
        # if user exists, redirect to login and set up session varibles 
        if user:  
            session['username'] = username
            session['user_id'] = user[0]
            return redirect('/')
    return render_template('login.html')


#  logout route
@app.route('/logout')
def logout():
    # remove session variables
    if 'user_id' in session:  
        session.pop('username', None)
        session.pop('user_id', None)
    return redirect('/')


# timer route
@app.route('/timer', methods=['GET', 'POST'])
def timer():
    # if user is not logged in, redirect to login page
    if 'user_id' not in session:  
        return redirect('/login')

    user_id = session.get('user_id')

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

    return render_template('timer.html', times=times)


if __name__ == '__main__':
    app.run(debug=True)
