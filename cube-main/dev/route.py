from flask import Flask, render_template, request, session, jsonify
import sqlite3
from base64 import b64encode
from secrets import token_hex

app = Flask(__name__)
app.config['SECRET_KEY'] = token_hex(32)  # Generate a random secret key for securing sessions


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
    # Connect to the database
    conn = sqlite3.connect('cube.db')
    cur = conn.cursor()
    # Execute query with parameters
    cur.execute(query, parameters)
    # Process results from the query
    if commit:
        conn.commit()
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
    # Default values for variables
    errors = {
        'empty_input': False,
        'exceed_limit': False,
    }
    check_username = {
        'query_result': None,
        'submit_form': False
    }
    username = None
    password = None
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
            # Get username and password from form
            username = request.form.get('username')
            password = request.form.get('password')
            # Check if inputs are empty or contain space
            if username == '' or password == '' or ' ' in username or ' ' in password:
                errors['empty_input'] = True
            # Check if inputs are longer than 10 characters
            elif len(username) > 10 or len(password) > 10:
                errors['exceed_limit'] = True
            # Get username from the database if inputs are valid
            if not errors['empty_input'] and not errors['exceed_limit']:
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
    sorting_way = 'id'  # Default sorting method for algoirthms
    valid_rating = True  # Flag for checking if the rating is valid
    is_space = False  # Flag for checking if the inputs has space or empty
    in_range = True  # Flag for chekcing if the inputs are within the range(0-5)
    if request.method == 'POST':
        # Form submission for how algoirthms are sorted
        if 'sorting-select' in request.form:
            sorting_way = request.form.get('sorting-select')

        # Form submission for rating
        if 'rating' in request.form:
            algorithm_id = request.form.get('algorithm_id')
            user_id = session.get('user_id')
            rating = request.form.get('rating')

            # Check if rating is not empty and does not contain spaces
            if rating == '' or ' ' in rating:
                is_space = True
            try:
                # Convert rating to an integer
                rating = int(rating)
                # Check if rating is within range
                if 0 > int(rating) or int(rating) > 5:
                    in_range = False
            except ValueError:
                in_range = False
            # Check if rating is valid
            if not in_range or is_space:
                valid_rating = False
            else:
                # Check if a rating already exists in the database
                check_rating = execute_query(
                    'SELECT * FROM ratings WHERE algorithm_id = ? AND user_id = ?',
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

    # Fetch the algorithms from the database
    if sorting_way == 'name':
        # Fetch algorithms from the database and order by algorithm name
        algorithms = execute_query(
            'SELECT * FROM algorithms WHERE algorithm_set=? ORDER BY name',
            (algorithm_set,), fetch_all=True
        )
    else:
        # Fetch algorithms from the database and order by algorithm id
        algorithms = execute_query(
            'SELECT * FROM algorithms WHERE algorithm_set=? ORDER BY id',
            (algorithm_set,), fetch_all=True
        )

    # Return an error page to user if the algorithms set does not exists in database
    if algorithms is None:
        return render_template('404.html')

    # Process algorithms' images to display in the website
    algorithms = [list(item) for item in algorithms]  # store all algorithms in a list
    images = []
    for algorithm in algorithms:
        image_blob = algorithm[-1]
        # Convert image value from blob to a base64 string
        if image_blob:
            encoded_image = b64encode(image_blob).decode('utf-8')
            img = [algorithm[1], encoded_image]
            images.append(img)

    # Fetch ratings from the database
    ratings = execute_query(
        'SELECT algorithm_id, ROUND(AVG(rating), 1) AS average_rating '
        'FROM ratings '
        'GROUP BY algorithm_id',
        fetch_all=True
    )
    # Store the query results in a dictionary
    ratings = {item[0]: item[1] for item in ratings}

    # Check if the request is an AJAX request
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
    username_exist = False  # Flag for checking if username exist in the database
    registered = False  # Flag for checking if user registered successfully

    # Check error for inputs from register form submission
    check_username, username, password, errors = check_account()
    # Check if inputs are valid
    if check_username['submit_form']:
        # Check if username exists
        if check_username['query_result'] is None:
            # Insert the new user account into the database
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
    wrong_username = False  # Flag for checking if user's username is correct
    wrong_password = False  # Flag for checking if user's password is correct

    # Check errors for input from login form
    check_username, username, password, errors = check_account()
    # Check if inputs are valid
    if check_username['submit_form']:
        # Check if username exists in database
        if check_username['query_result'] is None:
            # Set wrong username flag to True
            wrong_username = True
        else:
            # Check if password is correct
            check_password = execute_query(
                'SELECT * FROM users WHERE username = ? AND password = ?',
                (username, password,), fetch_one=True
            )
            if check_password is None:
                wrong_password = True
            else:
                # Set up session variables
                session['username'] = username
                session['user_id'] = check_password[0]

    return render_template(
        'login.html',
        wrong_username=wrong_username,
        wrong_password=wrong_password,
        exceed_limit=errors['exceed_limit'],
        empty_input=errors['empty_input']
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
    delete_account = False # Flag for checking if account is delected
    if request.method == 'POST':
        if 'delete' in request.form:
            # Form submission for delelte account and delete account in the database
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
            # Remove session variables
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
    # Check if user login
    if 'user_id' not in session:
        times = None  # Set times to None so the saved times in the database will not display
    else:
        user_id = session.get('user_id')
        if request.method == 'POST':
            if 'time' in request.form:
                # Save time in database
                time_value = request.form.get('time')
                execute_query(
                    'INSERT INTO timer (time, user_id) VALUES (?, ?)',
                    (time_value, user_id), commit=True
                )
            elif 'clear' in request.form:
                # Clear times in database
                execute_query(
                    'DELETE FROM timer WHERE user_id=?',
                    (user_id,), commit=True
                )
        # Fetch saved times from the database
        times = execute_query(
            'SELECT time FROM timer WHERE user_id=? ORDER BY id DESC',
            (user_id,), fetch_all=True
        )
    # Check if the request is an AJAX request
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
