

from flask import Flask, render_template, request
from flask import redirect, url_for, jsonify, flash

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Genre, Book, User

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json

from flask import make_response
import requests

import os
from werkzeug import secure_filename

from PIL import Image
from resizeimage import resizeimage

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

APPLICATION_NAME = "Book Catalog Application"


engine = create_engine('sqlite:///bookscatalogtest2.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

def allowed_file(filename):
    """
    Method to check for allowed format images to upload
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def createUser(login_session):
    """
    Method to create a new user in to the database.
    If successful returns the user id of the user.
    """
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    """
    Method returns the specific user object given the user id
    """
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    """
    Method returns the user id of an user given the email id.
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/login')
def showLogin():
    """
    This method shows the login page for the application
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
        for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    This method connects to the google signin page using OAuth
    """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps
            ('Current user is already connected.'),200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data.get('name')
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # See if user exists, if not create new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id


    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ " style = "width: 300px; height: 300px;
    border-radius: 150px;-webkit-border-radius: 150px;
    -moz-border-radius: 150px;"> """
    flash("You are now logged in as %s" % login_session.get('username'))
    print "done!"
    return output

    # DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    """
    This method logouts of the Google Signin
    """
    access_token = login_session.get('access_token')
    # print login_session.keys()
    # print 'In gdisconnect access token is %s', access_token
    # print 'User name is: '
    # print login_session.get('username')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']        #NOQA
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    # print 'result is '
    # print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('bookGenres'))
    else:

        response = make_response(json.dumps
            ('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response




@app.route('/genres/JSON')
def bookGenresJSON():
    """
    This method serves as the JSON endpoint for the all genres in the
    book catlaog
    """
    genres = session.query(Genre).order_by(Genre.name).all()
    return jsonify(Genres=[i.serialize for i in genres])

@app.route('/genre/books/<int:genre_id>/JSON')
def displayBooksJSON(genre_id):
    """
    This method serves as the JSON endpoint for all books in a
    specific genre.
    """
    books = session.query(Book).filter_by(genre_id = genre_id).all()
    return jsonify(Books=[i.serialize for i in books])

@app.route('/book/<int:genre_id>/<int:book_id>/JSON')
def BookJSON(genre_id, book_id):
    """
    This method serves as JSON endpoint for a specific book in a specific genre
    """
    book = session.query(Book).filter_by(genre_id=genre_id, id = book_id).one()
    return jsonify(Book=[book.serialize])

@app.route('/')
@app.route('/genres')
def bookGenres():
    """
    This method displays the main page of the Book Catalog Application.
    Main page displays all the genres in the app
    It also displays recently added 9 books into the application
    """
    genres = session.query(Genre).order_by(Genre.name).all()
    recent_books = session.query(Book).order_by(desc(Book.added_on)).all()
    error =''

    # Checks if any genres are available or not.
    if not genres:
        error = "There are no genres available currently!!"

    # Checks if user is logged in or not
    if 'username' not in login_session:
        return render_template('publicmain.html',genres = genres,
                                                 recent_books = recent_books,
                                                 error = error,
                                                 login_session = login_session)
    else:
        return render_template('main.html', genres = genres,
                                            recent_books = recent_books,
                                            error = error,
                                            login_session = login_session)


@app.route('/genre/new', methods =['GET','POST'])
def newGenre():
    """
    This method adds new genres into the application by
    valid logged in user.
    """
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if request.method == 'POST':
            newgenre = Genre(name = request.form['name'],
                user_id=login_session.get('user_id'))
            session.add(newgenre)
            session.commit()
            flash("New Genre added successfully!!")
            return redirect(url_for('bookGenres'))
        else:
            return render_template('addGenre.html',login_session=login_session)

@app.route('/genre/<int:genre_id>/edit', methods =['GET','POST'])
def editGenre(genre_id):
    """
    This method edits the details of a selected genre.
    Only those who has created that genre can edit the genre
    details.
    """
    genre = session.query(Genre).filter_by(id = genre_id).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if genre.user_id != login_session.get('user_id'):
            flash("You dont have permissions to update this genre!!")
            return redirect(url_for('bookGenres'))
        if request.method == 'POST':
            if request.form['name']:
                genre.name = request.form['name']
                session.add(genre)
                session.commit()
                flash("Genre updated successfully!!")
                return redirect(url_for('bookGenres'))
        else:
            return render_template('editGenre.html', genre = genre,
                                                 login_session = login_session)

@app.route('/genre/<int:genre_id>/delete', methods =['GET','POST'])
def deleteGenre(genre_id):
    """
    This method deletes the selected genre.
    """
    genre = session.query(Genre).filter_by(id = genre_id).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if genre.user_id != login_session.get('user_id'):
            flash("You dont have permissions to delete this genre!!")
            return redirect(url_for('bookGenres'))
        if request.method == 'POST':
            session.delete(genre)
            session.commit()
            flash("Genre deleted successfully!!")
            return redirect(url_for('bookGenres'))
        else:
            return render_template('deleteGenre.html', genre = genre,
                                                 login_session = login_session)

@app.route('/genre/books/<int:genre_id>')
def displayBooks(genre_id):
    """
    This method displays books in a selected genre.
    """
    books = session.query(Book).filter_by(genre_id = genre_id).all()
    genre = session.query(Genre).filter_by(id = genre_id).one()
    error = ''
    if not books:
        error = "Currently no books are avaialble in this genre"

    if 'username' not in login_session:
        return render_template('publicgenreBooks.html', books = books,
                                                        error = error,
                                                        genre = genre,
                                                login_session = login_session)
    else:
        return render_template('genreBooks.html', books = books,
                                                  error = error,
                                                  genre = genre,
                                                login_session = login_session)

@app.route('/book/<int:genre_id>/<int:book_id>')
def oneBook(book_id, genre_id):
    """
    This method displays details of a specific book selected from
    the catalog.
    """
    book = session.query(Book).filter_by(id = book_id).one()
    error =''
    if not book:
        error = "This book is not available"
    else:
        if 'username' not in login_session:
            return render_template('publicBook.html', book = book,
                                                      error = error,
                                                login_session = login_session)
        else:
            return render_template('book.html', book = book,
                                               error = error,
                                            login_session = login_session)



@app.route('/genre/books/<int:genre_id>/add', methods =['GET','POST'])
def addBook(genre_id):
    """
    This method adds a new book to the catalog.
    It takes given image and resize it to thumbanil size
    and saves it in the given folder.
    """
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if request.method == 'POST':
            if request.form['name'] and request.form['price']:
                newbook = Book(name = request.form['name'],
                               description = request.form['description'],
                               price = request.form['price'],
                               genre_id = genre_id,
                               user_id=login_session.get('user_id') )
                file = request.files['picture']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    with Image.open(file) as image:
                        image = resizeimage.resize_contain(image, [100, 150])

                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    newbook.picture = filename
                session.add(newbook)
                session.commit()
                flash("New book added successfully!!")
                return redirect(url_for('displayBooks', genre_id = genre_id))
        else:
            return render_template('addBook.html', genre_id = genre_id,
                                                   login_session = login_session)


@app.route('/book/<int:genre_id>/<int:book_id>/edit', methods =['GET','POST'])
def editBook(genre_id, book_id):
    """
    This method handles the editing of selected book.
    Only owner of the book would be able to edit the book.
    """
    book = session.query(Book).filter_by(id = book_id).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if book.user_id != login_session.get('user_id'):
            flash("You don't have permissions to edit this book!!")
            return redirect (url_for('displayBooks', genre_id = genre_id))

        if request.method == 'POST':
            book.name = request.form['name']
            book.description = request.form['description']
            book.price = request.form['price']
            session.add(book)
            session.commit()
            flash("Book updated successfully!!")
            return redirect (url_for('displayBooks', genre_id = genre_id))
        else:
            return render_template('editBook.html', genre_id = genre_id,
                                                     book = book,
                                                login_session = login_session)

@app.route('/book/<int:genre_id>/<int:book_id>/delete',methods =['GET','POST'])
def deleteBook(genre_id, book_id):
    """
    This method handles the deleting of selected book.
    Only owner of the book would be able to delete the book.
    """
    book = session.query(Book).filter_by(id = book_id).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if book.user_id != login_session.get('user_id'):
            flash("You don't have permissions to delete this book!!")
            return redirect (url_for('displayBooks', genre_id = genre_id))

        if request.method == 'POST':
            session.delete(book)
            session.commit()
            flash("Book deleted successfully!!")
            return redirect(url_for('displayBooks', genre_id = genre_id))
        else:
            return render_template('deleteBook.html', genre_id = genre_id,
                                                book= book,
                                                login_session = login_session)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)