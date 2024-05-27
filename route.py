from flask import Flask, render_template, request, redirect, session
import sqlite3
from base64 import b64encode
from secrets import token_hex
app = Flask(__name__)
app.config['SECRET_KEY'] = token_hex(32)


@app.route('/')
def homepage():
    return render_template('home.html')


@app.route('/algorithms/<algorithm_set>')
def algorithm(algorithm_set):
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM algorithms WHERE algorithm_set=?', (algorithm_set,))
    algorithms = cur.fetchall()
    conn.close()

    algorithms = [list(item) for item in algorithms]
    alg = []
    algs = []
    for algorithm in algorithms:
        image_blob = algorithm[-1]
        if image_blob is not None:
            encoded_image = b64encode(image_blob).decode('utf-8')
            algorithm[-1] = encoded_image
            alg.append(algorithm)
        else:
            algs.append(algorithm)

    return render_template('algorithms.html', alg=alg, algs=algs)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()

        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()

        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session['username'] = username
            session['user_id'] = user[0] 
            return redirect('/')
    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        conn = sqlite3.connect('cube.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM timer WHERE user_id=?', (session['user_id'],))
        conn.commit()
        conn.close()
        session.pop('username', None)
        session.pop('user_id', None)
    return redirect('/')



@app.route('/timer', methods=['GET', 'POST'])
def timer():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    if request.method == 'POST':
        if 'time' in request.form:
            time_value = request.form.get('time')
            conn = sqlite3.connect('cube.db')
            cur = conn.cursor()
            cur.execute('INSERT INTO timer (time, user_id) VALUES (?, ?)', (time_value, user_id))
            conn.commit()
            conn.close()
        elif 'clear' in request.form:
            conn = sqlite3.connect('cube.db')
            cur = conn.cursor()
            cur.execute('DELETE FROM timer WHERE user_id=?', (user_id,))
            conn.commit()
            conn.close()

    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute('SELECT time FROM timer WHERE user_id=?', (user_id,))
    times = cur.fetchall()
    conn.close()

    return render_template('timer.html', times=times)




if __name__ == '__main__':
    app.run(debug=True)
