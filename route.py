from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def homepage():
    return '(:'


@app.route('/about')
def about():
    return':('


@app.route('/algorithms/<algorithm_set>')
def algorithm(algorithm_set):
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM algorithms WHERE algorithm_set=?',(algorithm_set,))
    alg = cur.fetchall()
    conn.close()
    return render_template('algorithms.html', alg=alg)

if __name__ == '__main__':
    app.run(debug=True)