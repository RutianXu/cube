from flask import Flask, render_template, request, redirect, session
import sqlite3
from base64 import b64encode

app = Flask(__name__)
app.secret_key = 'a'


@app.route('/')
def homepage():
    return render_template('home.html')


@app.route('/algorithms/<algorithm_set>')
def algorithm(algorithm_set):
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM algorithms WHERE algorithm_set=?',(algorithm_set,))
    algorithms = cur.fetchall()
    conn.close()

    algorithms = [list(item) for item in algorithms]
    alg=[]
    algs=[]
    for algorithm in algorithms:
        image_blob = algorithm[-1]  
        if image_blob != None:
            encoded_image = b64encode(image_blob).decode('utf-8')
            algorithm[-1] = encoded_image
            alg.append(algorithm)
        else:
            algs.append(algorithm)
            
    return render_template('algorithms.html', alg=alg, algs=algs,)


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
            return redirect('/')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)