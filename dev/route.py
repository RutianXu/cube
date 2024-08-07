from flask import Flask, render_template, request, session
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
    Render the algorithms page and handle form submissions for sorting and rating

    Args:
        algorithm_set (str): The set of algorithms to display

    Returns:
        Render the algorithms template
        algorithms (list): List of algorithms to display
        images (list): List of images associated with the algorithms
        ratings (dict): Dictionary of average ratings and number of ratings for each algorithm
        algorithm_set (str): The name of the algorithms set to display
        sorting_way (str): Sorting method of the algoirthms
    """
    sorting_way = 'id'  # Default sorting method for algoirthms 
    if request.method == 'POST':
        # Form submission for how algoirthms are sorted
        if 'sorting-select' in request.form:
            sorting_way = request.form.get('sorting-select')

        # Form submission for rating
        if 'rating' in request.form:
            algorithm_id = request.form.get('algorithm_id')
            user_id = session.get('user_id')
            rating = request.form.get('rating')

            # Check if a rating already exists in the database
            check_rating = execute_query(
                'SELECT * FROM ratings WHERE algorithm_id = ? AND user_id = ?',
                (algorithm_id, user_id,), fetch_one=True
            )
            if check_rating is None:  # Check if user rated the same algorithm 
                # Insert rating into the database if the user have not rated before
                execute_query(
                    'INSERT INTO ratings (algorithm_id, user_id, rating) VALUES (?, ?, ?)',
                    (algorithm_id, user_id, rating,), commit=True
                )
            else:
                # Update rating if the user have rated before
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

    # Process algorithms' images for display in the website
    algorithms = [list(item) for item in algorithms]  # store all algorithms in a list
    images = []
    for algorithm in algorithms:
        image_blob = algorithm[-1]
        # Change image value from blob to a base64 string
        if image_blob:
            encoded_image = b64encode(image_blob).decode('utf-8')
            img = [algorithm[1], encoded_image]
            images.append(img)

    # Fetch ratings from the database
    ratings = execute_query(
        'SELECT algorithm_id, ROUND(AVG(rating), 1) AS average_rating, '
        'COUNT(rating) AS num_ratings '
        'FROM ratings '
        'GROUP BY algorithm_id',
        fetch_all=True
    )
    # Store the query results in a dictionary
    ratings = {item[0]: item[1] for item in ratings}

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
        Render register template
        username_exist (bool): Flag indicating if the username already exists
        registered (bool): Flag indicating if registration was successful
    """
    username_exist = False  # Flag for checking if username exist in the database
    registered = False  # Flag for checking if user registered successfully

    if request.method == 'POST':
        # Form submission for register form
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the username already exists in the database
        check_username = execute_query(
            'SELECT * FROM users WHERE username=?',
            (username,), fetch_one=True
        )
        if check_username is None:
            # Insert the new user account into the database
            execute_query(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, password), commit=True
            )
            registered = True
        else:
            # Tell the user to use a different username
            username_exist = True

    return render_template(
        'register.html',
        username_exist=username_exist,
        registered=registered
    )


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login and render the login page

    Returns:
        Render login template
        logged_in (bool): Flag indicating if the user is logged in
        wrong_username (bool): Flag indicating if the username is incorrect
        wrong_password (bool): Flag indicating if the password is incorrect
    """
    logged_in = False  # Flag for checking if user is logged in for direct them to homepage
    wrong_username = False  # Flag for checking if user's username is correct
    wrong_password = False  # Flag for checking if user's password is correct

    if request.method == 'POST':
        # Form submission for login
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if user account exists
        check_user = execute_query(
            'SELECT COUNT(*) AS user_count FROM users WHERE username = ?',
            (username,), fetch_one=True
        )
        if check_user[0] == 1:
            # Check if the password is correct
            check_password = execute_query(
                'SELECT * FROM users WHERE username = ? AND password = ?',
                (username, password,), fetch_one=True
            )
            if check_password is None:
                wrong_password = True
            else:
                # Set up session variables
                logged_in = True
                session['username'] = username
                session['user_id'] = check_password[0]
        else:
            wrong_username = True

    return render_template(
        'login.html',
        logged_in=logged_in,
        wrong_username=wrong_username,
        wrong_password=wrong_password
    )


# Logout route
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Handle user logout and account deletion, and render the logout page.

    Returns:
        Render logout template
        logged_out (bool): Flag indicating if the user has logged out
        delete_account (bool): Flag indicating if the account has been deleted
    """
    logged_out = False  # Flag for checking if user logged out
    delete_account = False  # Flag for checking if account deleted
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
        if 'logout' in request.form:
            # Form submisstion for logout
            logged_out = True
        if 'logout' in request.form or 'delete' in request.form:
            # Remove session variables
            session.pop('username')
            session.pop('user_id')

    return render_template(
        'logout.html',
        logged_out=logged_out,
        delete_account=delete_account
    )


# Timer route
@app.route('/timer', methods=['GET', 'POST'])
def timer():
    """
    Render the timer page and handle form submissions for saving and clearing times

    Returns:
        Render timer template
        times (list or None): List of saved times or None if the user is not logged in.
        logged_in (bool): Flag indicating if the user is logged in.
    """
    # Check if user login
    if 'user_id' not in session:
        logged_in = False  # Flag for checking if user is logged in
        times = None  # Set times to None so the saved times in the database will not display
    else:
        user_id = session.get('user_id')
        logged_in = True
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
            'SELECT time FROM timer WHERE user_id=?',
            (user_id,), fetch_all=True
        )

    return render_template(
        'timer.html',
        times=times,
        logged_in=logged_in
    )


# Notation route
@app.route('/notation')
def notation():
    """
    Render the notation page.

    Returns:
        Render notation template
    """
    return render_template('notation.html')


# 404 route
@app.errorhandler(404)
def page_not_found(error):
    """
    Handle 404 errors and render the 404 error page.

    Returns:
        Render 404 template
    """
    return render_template('404.html')


if __name__ == '__main__':
    app.run(debug=True)
