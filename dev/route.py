from flask import Flask, render_template, request, session, jsonify
import sqlite3
from base64 import b64encode
from secrets import token_hex


app = Flask(__name__)
app.config['SECRET_KEY'] = token_hex(32)


# Function to execute queries
def execute_query(query, parameters=(), fetch_one=False, fetch_all=False, commit=False):
    """
    Execute a SQL query with optional parameters

    Args:
        query (str): SQL query to execute
        parameters (tuple): Parameters to pass to the query
        fetch_one (bool): Whether to fetch a single result
        fetch_all (bool): Whether to fetch all results
        commit (bool): Whether to commit results

    Returns:
        result: Query result or None
    """
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    cur.execute(query, parameters)
    # Fetch or commit results from the query
    if commit:
        conn.commit()
        # Set result to None because no data is fecthed
        result = None
    elif fetch_one:
        result = cur.fetchone()
    elif fetch_all:
        result = cur.fetchall()
    conn.close()
    return result


def check_account():
    """
    Check user account in the database and validate inputs

    Returns:
        check_account (dict): Result from querying the database for the account
        username (str): The username from the form
        password (str): The password from the form
        errors (dict): A dictionary of the possible errors of inputs
    """
    errors = {
        'empty_input': False,
        'exceed_limit': False,
        'short_password': False,
    }
    check_username = {
        'query_result': None,
        'submit_form': False
    }
    username = None
    password = None
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
            username = request.form.get('username')
            password = request.form.get('password')

            # Error checking for username and password
            if username == '' or password == '' or ' ' in username or ' ' in password:
                errors['empty_input'] = True
            elif len(password) < 6:
                errors['short_password'] = True
            elif len(username) > 10 or len(password) > 10:
                errors['exceed_limit'] = True

            # Get username from the database if the inputs are valid
            if not errors['empty_input'] and not errors['exceed_limit'] and not errors['short_password']:
                check_username['query_result'] = execute_query(
                    'SELECT * FROM users WHERE username=?',
                    (username,), fetch_one=True
                )
                check_username['submit_form'] = True
    return check_username, username, password, errors


# Homepage route
@app.route('/')
def homepage():
    """
    Render the homepage template
    """
    return render_template('home.html')


# Algorithm route
@app.route('/algorithms/<algorithm_set>', methods=['GET', 'POST'])
def algorithm(algorithm_set):
    """
    Render the algorithms page and handle form submissions for sorting and rating.

    Args:
        algorithm_set (str): The set of algorithms to display.

    Returns:
        Render the algorithms template:
        - algorithms (list): List of algorithms to display.
        - images (list): List of images associated with the algorithms.
        - ratings (dict): Dictionary of average ratings and number of ratings for each algorithm.
        - algorithm_set (str): The name of the algorithms set to display.
        - sorting_way (str): Sorting method of the algorithms.

        JSON response:
        - response (dict):
            - valid_rating (bool): Whether the rating submitted is valid.
            - is_space (bool): Whether the rating contains space or empty.
            - in_range (bool): Whether the rating is within the allowed range (0-5).
            - ratings (dict): Updated average ratings for algorithms.
    """
    sorting_way = 'id'
    valid_rating = True
    is_space = False
    in_range = True
    if request.method == 'POST':
        if 'sorting-select' in request.form:
            sorting_way = request.form.get('sorting-select')
        if 'rating' in request.form:
            algorithm_id = request.form.get('algorithm_id')
            user_id = session.get('user_id')
            rating = request.form.get('rating')

            # Error checking for rating input
            if rating == '' or ' ' in rating:
                is_space = True
            try:
                rating = int(rating)
                if 0 > rating or rating > 5:
                    in_range = False
            except ValueError:
                in_range = False

            # Check if rating is valid
            if not in_range or is_space:
                valid_rating = False
            else:
                # Check if a rating already exists in the database
                check_rating = execute_query(
                    'SELECT rating FROM ratings WHERE algorithm_id = ? AND user_id = ?',
                    (algorithm_id, user_id,), fetch_one=True
                )
                if check_rating is None:
                    # Insert rating into the database if the user has not rated before
                    execute_query(
                        'INSERT INTO ratings (algorithm_id, user_id, rating) VALUES (?, ?, ?)',
                        (algorithm_id, user_id, rating,), commit=True
                    )
                else:
                    # Update rating if the user has rated before
                    execute_query(
                        'UPDATE ratings SET rating = ? WHERE user_id = ? AND algorithm_id = ?',
                        (rating, user_id, algorithm_id,), commit=True
                    )

    # Sorting and fetch ssssalgorithms
    if sorting_way == 'name':
        algorithms = execute_query(
            'SELECT id, name, notations, image FROM algorithms WHERE algorithm_set=? ORDER BY name',
            (algorithm_set,), fetch_all=True
        )
    else:
        algorithms = execute_query(
            'SELECT id, name, notations, image FROM algorithms WHERE algorithm_set=? ORDER BY id',
            (algorithm_set,), fetch_all=True
        )

    # Render a 404 page if the algorithms set does not exists in the database
    if algorithms is None:
        return render_template('404.html')

    # Change image values from BLOB to a base64 string
    algorithms = [list(item) for item in algorithms]
    images = []  # Stores images separately to the algorithms
    for algorithm in algorithms:
        image_blob = algorithm[-1]
        if image_blob:
            encoded_image = b64encode(image_blob).decode('utf-8')
            img = [algorithm[1], encoded_image]
            images.append(img)

    # Fetch and calculates average rating from the database
    ratings = execute_query(
        'SELECT algorithm_id, ROUND(AVG(rating), 1) AS average_rating '
        'FROM ratings '
        'GROUP BY algorithm_id',
        fetch_all=True
    )
    ratings = {item[0]: item[1] for item in ratings}

    # Check if the request is an AJAX request for updating new average rating
    if request.headers.get('rating') == 'XMLHttpRequest':
        response = {
            'valid_rating': valid_rating,
            'is_space': is_space,
            'in_range': in_range,
            'ratings': ratings
        }
        return jsonify(response)

    return render_template(
        'algorithms.html',
        algorithms=algorithms,
        images=images,
        ratings=ratings,
        algorithm_set=algorithm_set,
        sorting_way=sorting_way
    )


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration and render the registration page

    Returns:
        Render the register template:
        - username_exist (bool): Flag indicating if the username already exists.
        - registered (bool): Flag indicating if registration was successful.
        - empty_input (bool): Flag indicating if inputs from forms are emtpy or have space.
        - exceed_limit (bool): Flag indicatin if inputs are longer than 10 characters.
    """
    username_exist = False
    registered = False
    check_username, username, password, errors = check_account()

    if check_username['submit_form']:
        if check_username['query_result'] is None:  # Check if username exists
            execute_query(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, password), commit=True
            )
            registered = True
        else:
            username_exist = True
    return render_template(
        'register.html',
        username_exist=username_exist,
        registered=registered,
        exceed_limit=errors['exceed_limit'],
        empty_input=errors['empty_input'],
        short_password=errors['short_password']
    )


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login and render the login page

    Returns:
        Render the login template:
        - wrong_username (bool): Flag indicating if the username is incorrect.
        - wrong_password (bool): Flag indicating if the password is incorrect.
        - empty_input (bool): Flag indicating if inputs from forms are emtpy or have space.
        - exceed_limit (bool): Flag indicatin if inputs are longer than 10 characters.
    """
    wrong_username = False
    wrong_password = False
    check_username, username, password, errors = check_account()

    if check_username['submit_form']:
        if check_username['query_result'] is None:  # Check if username exists
            wrong_username = True
        else:
            # Check if password is correct
            check_password = execute_query(
                'SELECT id FROM users WHERE username = ? AND password = ?',
                (username, password,), fetch_one=True
            )
            if check_password is None:
                wrong_password = True
            else:
                session['username'] = username
                session['user_id'] = check_password[0]

    return render_template(
        'login.html',
        wrong_username=wrong_username,
        wrong_password=wrong_password,
        exceed_limit=errors['exceed_limit'],
        empty_input=errors['empty_input'],
        short_password=errors['short_password']
    )


# Logout route
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Handle user logout and account deletion, and render the logout page.

    Returns:
        Render the logout template:
        - delete_account (bool): Flag indicating if the account has been deleted.
    """
    delete_account = False
    if request.method == 'POST':
        if 'delete' in request.form:
            user_id = session.get('user_id')
            execute_query(
                'DELETE FROM users WHERE id = ?',
                (user_id,), commit=True
            )
            execute_query(
                'DELETE FROM ratings WHERE user_id = ?',
                (user_id,), commit=True
            )
            execute_query(
                'DELETE FROM timer WHERE user_id = ?',
                (user_id,), commit=True
            )
            delete_account = True
        if 'logout' in request.form or 'delete' in request.form:
            session.pop('username')
            session.pop('user_id')

    return render_template(
        'logout.html',
        delete_account=delete_account
    )


# Timer route
@app.route('/timer', methods=['GET', 'POST'])
def timer():
    """
    Render the timer page and handle form submissions for saving and clearing times

    Returns:
        Render the timer template:
        - times (list or None): List of saved times or None if the user is not logged in.

        JSON response:
            - times (list): List of new saved times to update in the website.
    """
    if 'user_id' not in session:
        times = None  # Set times to None so the times in the database will not display
    else:
        user_id = session.get('user_id')
        if request.method == 'POST':
            if 'time' in request.form:
                time_value = request.form.get('time')
                execute_query(
                    'INSERT INTO timer (time, user_id) VALUES (?, ?)',
                    (time_value, user_id), commit=True
                )
            elif 'clear' in request.form:
                execute_query(
                    'DELETE FROM timer WHERE user_id=?',
                    (user_id,), commit=True
                )

        times = execute_query(
            'SELECT time FROM timer WHERE user_id=? ORDER BY id DESC',
            (user_id,), fetch_all=True
        )
    # Check if the request is an AJAX request so times are updated on the website
    if request.headers.get('time') == 'XMLHttpRequest':
        return jsonify(times)

    return render_template(
        'timer.html',
    )


# Notation route
@app.route('/notation')
def notation():
    """
    Render the notation page.
    """
    return render_template('notation.html')


# 404 route
@app.errorhandler(404)
def page_not_found(error):
    """
    Render the 404 error page.
    """
    return render_template('404.html')


if __name__ == '__main__':
    app.run(debug=True)
