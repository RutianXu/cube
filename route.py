from flask import Flask, render_template
import sqlite3
import base64

app = Flask(__name__)

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
            encoded_image = base64.b64encode(image_blob).decode('utf-8')
            algorithm[-1] = encoded_image
            alg.append(algorithm)
        else:
            algs.append(algorithm)
            
    return render_template('algorithms.html', alg=alg, algs=algs,)

if __name__ == '__main__':
    app.run(debug=True)