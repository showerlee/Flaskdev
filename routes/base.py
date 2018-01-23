from flask import render_template, flash, redirect, url_for, session, request, jsonify
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from wtforms.fields.html5 import EmailField
from passlib.hash import sha256_crypt
from utils.wraps import is_logged_in, is_active, is_admin
from utils.paginate import paginate
from . import routes
from utils.dbconn import mysql
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from utils.upload import photos
from datetime import datetime
import time


@routes.context_processor
def inject_global_setting():
    def setting(field):
        # Create cursor
        cur = mysql.connection.cursor()

        field_dict ={'siteurl': '',
                    'home': '',
                    'bloghome': '',
                    'blogdescription': '',
                    'admin_email': '',
                    'users_can_register': ''}

        for key, val in field_dict.items():

            # Get all setting
            res1 = cur.execute("SELECT * FROM options WHERE option_name = %s", (str(key),))

            db_options = cur.fetchone()

            field_dict[key] = db_options['option_value'] if key != 'users_can_register' else int(db_options['option_value'])


        cur.close()

        return field_dict[field]

    return dict(setting=setting)


@routes.errorhandler(404)
def page_not_found(e):
    return render_template("base/404.html")


@routes.errorhandler(405)
def method_not_found(e):
    return render_template("base/405.html")


# Index
@routes.route('/')
def index():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get posts
    res1 = cur.execute("SELECT p.id, p.post_title, p.post_author, p.post_content, p.post_date, p.post_modified, p.post_count, t.name AS category FROM posts p LEFT JOIN terms t ON p.post_parent = t.term_id ORDER BY p.id DESC LIMIT 8")

    posts = cur.fetchall()

    # Write site_url to DB
    field_list = ['siteurl', 'home']

    for field in field_list:
        res2 = cur.execute("SELECT option_value FROM options WHERE option_name=%s", (field,))
        db_field = cur.fetchone()

        if db_field['option_value'] == '':
            site_url = request.base_url
            res3 = cur.execute("UPDATE options SET option_value=%s WHERE option_name=%s", (site_url, field))
            # Commit to DB
            mysql.connection.commit()

    if res1 > 0:
        return render_template('base/home.html', posts=posts)
    else:
        msg = 'No posts Found.'
        return render_template('base/home.html', msg=msg)
    # Close connection
    cur.close()


# About
@routes.route('/about/')
def about():
    return render_template('base/about.html')


# posts
@routes.route('/posts/<string:category>/')
@routes.route('/posts/<string:category>/<int:page>/')
def posts(page=1, category='default'):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get posts
    res1 = cur.execute("SELECT p.id, p.post_title, p.post_author, p.post_content, p.post_date, p.post_modified, p.post_count, t.name AS category FROM posts p LEFT JOIN terms t ON p.post_parent = t.term_id WHERE t.alias=%s ORDER BY p.id DESC", [category])
    posts = cur.fetchall()

    res2 = cur.execute("SELECT * FROM terms")
    terms = cur.fetchall()

    # Close connection
    cur.close()

    if res1 > 0:
        # Each page size
        page_size = 12

        # Paginated posts list
        posts_cut = list(paginate(posts, page_size))

        # Page number list
        page_list = list(range(1, len(posts_cut) + 1))

        if page > 0 and page < len(posts_cut) + 1:
            return render_template('base/posts.html', posts=posts_cut[page - 1],
                                   page=page, page_list=page_list, terms=terms, category=category)
        else:
            return redirect(url_for('.posts'))
    else:
        msg = 'No posts Found.'
        posts = ''
        return render_template('base/posts.html', msg=msg, posts=posts, terms=terms, category=category)


# Comment Form Class
class CommentForm(Form):
    comment = TextAreaField('', [validators.Length(min=10)])


# Single post
@routes.route('/post/<string:id>/', methods=['GET', 'POST'])
def post(id):
    # Create cursor
    conn = mysql.connection
    cur = conn.cursor()
    # Get post
    result = cur.execute("SELECT * FROM posts WHERE id = %s", [id])

    post_old = cur.fetchone()

    # Update post_count
    cur.execute("UPDATE posts SET post_count = %s WHERE id = %s", [
                post_old['post_count'] + 1, id])

    # result = cur.execute("SELECT * FROM posts WHERE id = %s", [id])
    result = cur.execute("SELECT p.id, p.post_title, p.post_author, p.post_content, p.post_date, p.post_modified, p.post_count, p.post_parent, t.name AS category FROM posts p LEFT JOIN terms t ON p.post_parent = t.term_id WHERE p.id = %s", [id])
    post = cur.fetchone()

    conn.commit()

    # Get comment
    result = cur.execute("SELECT c.id, c.comm_author, c.comm_content, c.comm_date, c.comm_modified FROM comments c, posts p WHERE c.comm_post = p.id AND p.id = %s ORDER BY c.id DESC", (id,))
    comments = cur.fetchall()

    form = CommentForm(request.form)

    if request.method == 'POST' and form.validate():
        comment = request.form['comment']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO comments(comm_author, comm_content, comm_post) VALUES(%s, %s, %s)",
                    (session['fullname'], comment, id))

        # Commit to DB
        mysql.connection.commit()

        flash('Comment created...', 'success')

        return redirect('/post/%s' %(id))

    cur.close()

    return render_template('base/post.html', post=post, form=form, comments=comments)


# Register Form Class
class RegisterForm(Form):
    fullname = StringField('Fullname <span class="text-danger">*</span>', [validators.Length(min=6, max=50)])
    username = StringField('Username <span class="text-danger">*</span>', [validators.Regexp(
        '\w+$', message="Name must contain only letters numbers or underscore"), validators.Length(min=5, max=25)])
    email = EmailField('Email <span class="text-danger">*</span>', [validators.Length(
        min=6, max=50), validators.Email()])
    password = PasswordField('Password <span class="text-danger">*</span>', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match'),
        validators.Length(min=6, max=25)
    ])
    confirm = PasswordField('Confirm Password <span class="text-danger">*</span>')
    code = StringField('Invitation Code <span class="text-danger">*</span>', [validators.DataRequired()])


# User Register
@routes.route('/register/', methods=['GET', 'POST'])
def register():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get register id
    res = cur.execute("SELECT option_value FROM options WHERE option_name='users_can_register'")

    db_register = cur.fetchone()

    form = RegisterForm(request.form)

    if int(db_register['option_value']) == 1:
        if request.method == 'POST' and form.validate():
            fullname = form.fullname.data
            email = form.email.data
            username = form.username.data
            password = sha256_crypt.encrypt(str(form.password.data))
            code = form.code.data

            # Create cursor
            cur = mysql.connection.cursor()

            # Get invitation code
            res1 = cur.execute("SELECT code FROM invitation")

            db_code = cur.fetchall()

            res2 = cur.execute("SELECT username FROM users")

            db_username = cur.fetchall()

            if username.lower() not in list(map(lambda i: i['username'], db_username)):

                if code in list(map(lambda i: i['code'], db_code)):
                    # Insert user info
                    cur.execute("INSERT INTO users(fullname, email, username, password) VALUES(%s, %s, %s, %s)",
                                (fullname, email.lower(), username.lower(), password))

                    # Commit to DB
                    mysql.connection.commit()

                    flash('You are now registered and can log in.', 'success')

                    return redirect(url_for('.login'))
                else:
                    error = 'Invalid invitation code, please try it again.'
                    return render_template('base/register.html', form=form, error=error)

            else:
                error = 'Username "%s" exists, please try another one.' % username
                return render_template('base/register.html', form=form, error=error)

            # Close connection
            cur.close()

        return render_template('base/register.html', form=form)
    else:
        flash('Registation disabled, please contact admin for further assistance', 'warning')
        return redirect(url_for('.index'))


# Register Form Class
class ChangePassForm(Form):
    curr_pass = PasswordField('Current Password')
    new_pass = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match.'),
        validators.Length(min=6, max=25)
    ])
    confirm = PasswordField('Confirm New Password')


# User Change password
@routes.route('/changepass/', methods=['GET', 'POST'])
@is_logged_in
@is_active
def changepass():
    form = ChangePassForm(request.form)

    username = session['username']
    # Create cursor
    cur = mysql.connection.cursor()

     # Get user by username
    res = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

    if res > 0:
        data = cur.fetchone()
        db_password = data['password']

        if request.method == 'POST' and form.validate():
            curr_password = form.curr_pass.data
            new_password = sha256_crypt.encrypt(str(form.new_pass.data))

            # Compare Passwords
            if sha256_crypt.verify(curr_password, db_password):
                cur.execute("UPDATE users SET password = %s WHERE username = %s", [
                            new_password, username])

                # Commit to DB
                mysql.connection.commit()

                flash('Password changed successfully.', 'success')
                return redirect(url_for('.index'))
            else:
                error = 'Invalid current password, please try it again.'
                return render_template('base/change_pass.html', error=error, form=form, data=data)
    else:
        error = 'Username not found.'
        return render_template('base/change_pass.html', error=error, form=form, data=data)

    # Close connection
    cur.close()

    return render_template('base/change_pass.html', form=form, data=data)


# User login
@routes.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']
            fullname = data['fullname']
            user_role = data['user_role']
            user_status = data['user_status']
            avatar = data['avatar']
            user_id = data['id']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                session['fullname'] = fullname
                session['user_role'] = user_role
                session['user_status'] = user_status
                session['avatar'] = avatar
                session['user_id'] = user_id

                if session['user_status'] == 1:
                    flash('You are now logged in', 'success')
                    return redirect(url_for('.index'))
                else:
                    flash('Unauthorized, Please check if your account is disabled.', 'danger')
                    return redirect(url_for('.login'))    
            else:
                error = 'Incorrect password, please try it again.'
                return render_template('base/login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found.'
            return render_template('base/login.html', error=error)

    return render_template('base/login.html')


# Profile Form Class
class ProfileForm(Form):
    fullname = StringField('Fullname <span class="text-danger">*</span>', [validators.Length(min=6, max=50)])
    email = EmailField('Email <span class="text-danger">*</span>', [validators.Length(
        min=6, max=50), validators.Email()])
    description = TextAreaField(
        'Description', [validators.Length(min=0, max=1000)])


# Edit profile
@routes.route('/edit_profile/', methods=['GET', 'POST'])
@is_logged_in
@is_active
def edit_profile():

    username = session['username']

    # Create cursor
    cur = mysql.connection.cursor()

    # Get user info by username
    res1 = cur.execute("SELECT * FROM users WHERE username = %s", [username])
    user_info = cur.fetchone()

    res2 = cur.execute("SELECT u.username, r.role, u.fullname, u.avatar FROM users u, roles r WHERE u.user_role = r.id and u.username = %s", [username])

    db_users = cur.fetchone()

    cur.close()
    # Get form
    form = ProfileForm(request.form)

    # Populate post form fields
    form.fullname.data = user_info['fullname']
    form.email.data = user_info['email']
    form.description.data = user_info['description']

    if request.method == 'POST' and form.validate():
        fullname = request.form['fullname']
        email = request.form['email']
        description = request.form['description']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute(
            "UPDATE users SET fullname=%s, email=%s, description=%s WHERE username=%s", (fullname, email, description, username))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        # Change session fullname
        session['fullname'] = fullname

        flash('Profile Updated.', 'success')

        return redirect(url_for('.edit_profile'))

    return render_template('base/edit_profile.html', form=form, db_users=db_users)


class UploadForm(FlaskForm):
    photo = FileField(validators=[FileAllowed(['jpg', 'png'], u'Image only!'), FileRequired(u'File was empty!')])


@routes.route('/upload/', methods=['GET', 'POST'])
@is_logged_in
@is_active
def upload_file():
    # Get session username
    username = session['username']

    # Create Cursor
    cur = mysql.connection.cursor()

    res1 = cur.execute("SELECT u.username, r.role, u.fullname, u.avatar FROM users u, roles r WHERE u.user_role = r.id and u.username = %s", [username])

    db_users = cur.fetchone()

    form = UploadForm()
    username = session['username']

    if form.validate_on_submit():
        filename = photos.save(form.photo.data, folder=username, name=str(int(time.time()))+'.')
        file_url = photos.url(filename)
        # flash(file_url)
        avatar = file_url.split('/')[-1]

        res2 = cur.execute("SELECT u.username, r.role, u.fullname, u.avatar FROM users u, roles r WHERE u.user_role = r.id and u.username = %s", [username])

        db_users = cur.fetchone()

        # Execute
        cur.execute(
            "UPDATE users SET avatar=%s WHERE username=%s", (avatar, username))

        # Commit to DB
        mysql.connection.commit()

        # Update session avatar
        session['avatar'] = avatar

        flash('Avatar Updated.', 'success')
        return redirect(url_for('.edit_profile'))
    else:
        file_url = None

    # Close connection
    cur.close()

    return render_template('base/upload.html', form=form, db_users=db_users, file_url=file_url)


# Comment Edit Form Class
class CommEditForm(Form):
    comment = TextAreaField('', [validators.Length(min=10)])

# Edit comment
@routes.route('/edit_comment/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def edit_comment(id):
    # Get form
    form = CommEditForm(request.form)

    # Create cursor
    cur = mysql.connection.cursor()

    # Get user by id
    res1 = cur.execute("SELECT c.comm_content, p.id FROM comments c, posts p WHERE c.comm_post = p.id AND c.id = %s", [id])

    db_comment = cur.fetchone()

    cur.close()

    # Populate comment form fields
    form.comment.data = db_comment['comm_content']
    post_id = db_comment['id']

    if request.method == 'POST' and form.validate():
        comment = request.form['comment']

        # Create Cursor
        cur = mysql.connection.cursor()

        modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cur.execute("UPDATE comments SET comm_content=%s, comm_modified=%s WHERE id=%s", (comment, modified, id))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Comments Updated.', 'success')

        return redirect('/post/%s' % (post_id))

    return render_template('base/edit_comment.html', form=form, db_comment=db_comment)


# Logout
@routes.route('/logout/')
@is_logged_in
@is_active
def logout():
    session.clear()
    flash('You are now logged out.', 'success')
    return redirect(url_for('.login'))
