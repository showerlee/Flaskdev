from flask import render_template, flash, redirect, url_for, session, request, jsonify
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField, RadioField
from wtforms.fields.html5 import EmailField
from passlib.hash import sha256_crypt
from datetime import datetime
from utils.wraps import is_logged_in, is_active, is_admin
from utils.paginate import paginate
from . import routes
from utils.dbconn import mysql


# Dashboard
@routes.route('/admin/posts/')
@routes.route('/admin/posts/<int:page>/')
@is_logged_in
@is_active
@is_admin
def admin_posts(page=1):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get posts
    result = cur.execute("SELECT p.id, p.post_title, p.post_author, p.post_content, p.post_date, p.post_modified, p.post_count, t.name AS category FROM posts p LEFT JOIN terms t ON p.post_parent = t.term_id ORDER BY p.id DESC")

    if result > 0:
        posts = cur.fetchall()

        # Each page size
        page_size = 15

        # Paginated posts list
        posts_cut = list(paginate(posts, page_size))

        # Page number list
        page_list = list(range(1, len(posts_cut) + 1))

        # Close connection
        cur.close()

        if page > 0 and page < len(posts_cut) + 1:
            return render_template('admin/admin_posts.html', posts=posts_cut[page - 1],
                                   page=page, page_list=page_list)
        else:
            return redirect(url_for('.admin_posts'))
    else:
        msg = 'No posts Found.'
        posts = ''
        return render_template('admin/admin_posts.html', msg=msg, posts=posts)


# # Dashboard
# @routes.route('/dashboard/')
# @is_logged_in
# def dashboard():
#     # Create cursor
#     cur = mysql.connection.cursor()

#     # Get posts
#     result = cur.execute("SELECT * FROM posts order by id desc")

#     posts = cur.fetchall()

#     if result > 0:
#         return render_template('base/dashboard.html', posts=posts)
#     else:
#         msg = 'No posts Found.'
#         return render_template('base/dashboard.html', msg=msg)
#     # Close connection
#     cur.close()


# post Form Class
class PostForm(Form):
    title = StringField('Title <span class="text-danger">*</span>', [validators.Length(min=1, max=200)])
    content = TextAreaField('Content <span class="text-danger">*</span>', [validators.Length(min=30)])
    category = SelectField('Category', coerce=int)


# Add post
@routes.route('/admin/add_post/', methods=['GET', 'POST'])
@is_logged_in
@is_active
def admin_add_post():
    form = PostForm(request.form)
    # Create cursor
    cur = mysql.connection.cursor()

    # Get invitation code
    res = cur.execute("SELECT * FROM terms order by term_id ASC")

    db_terms = cur.fetchall()

    # Get all category list
    name_list = list(map(lambda i: (i['term_id'], i['name']), db_terms))

    # Populate (id, name) form fields
    form.category.choices = name_list

    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data
        category = request.form['category']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO posts(post_title, post_content, post_author, post_parent) VALUES(%s, %s, %s, %s)",
                    (title, content, session['fullname'], category))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Post Created...', 'success')

        return redirect('/posts/default/')

    return render_template('admin/admin_add_post.html', form=form)


# Edit posts
@routes.route('/admin/edit_post/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
def edit_post(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get post by id
    res1 = cur.execute("SELECT * FROM posts WHERE id = %s", [id])

    posts = cur.fetchone()

    # Get all category list
    res2 = cur.execute("SELECT * FROM terms order by term_id ASC")

    cates_all = cur.fetchall()

    # Populate (id, name) form fields from category
    name_list = list(map(lambda i: (i['term_id'], i['name']), cates_all))

    cur.close()

    # Get form
    form = PostForm(request.form)

    # Populate post form fields
    form.title.data = posts['post_title']
    form.content.data = posts['post_content']
    form_id = posts['id']
    form.category.choices = name_list
    form.category.process_data(posts['post_parent'])

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        content = request.form['content']
        modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        post_parent = request.form['category']

        # Create Cursor
        cur = mysql.connection.cursor()
        # Execute
        cur.execute(
            "UPDATE posts SET post_title=%s, post_content=%s, post_modified=%s, post_parent=%s WHERE id=%s", (title, content, modified, post_parent, id))
        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Post Updated.', 'success')

        return redirect('/admin/edit_post/%s/' % id)

    return render_template('admin/admin_edit_post.html', form=form, form_id=form_id)


# Delete post
@routes.route('/delete_post/<string:id>/', methods=['POST'])
@is_logged_in
@is_active
@is_admin
def delete_post(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM posts WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Post Deleted.', 'success')

    return redirect(url_for('.admin_posts'))


# Scraping test page
@routes.route('/scrapingtest/')
def scrapingtest():
    try:
        return render_template("base/scrapingtest.html")
    except Exception as e:
        return(str(e))


# Admin entry
@routes.route('/admin/')
@is_logged_in
@is_active
@is_admin
def admin():
    try:
        return render_template("admin/admin.html")
    except Exception as e:
        return(str(e))


# Category Form Class
class CategoryForm(Form):
    name = StringField('Name <span class="text-danger">*</span>', [validators.Regexp('\w+$', message="Name must contain only letters numbers or underscore"),
                                validators.Length(min=2, max=25)])
    alias = StringField('Alias', [validators.Length(min=0, max=25)])
    description = TextAreaField(
        'Description', [validators.Length(min=0, max=200)])
    parent = SelectField('Parent category', coerce=int)


# Category entry
@routes.route('/admin/category/', methods=['GET', 'POST'])
@routes.route('/admin/category/<int:page>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_category(page=1):
    form = CategoryForm(request.form)
    action = 'Add a new category'

    # Create cursor
    cur = mysql.connection.cursor()

    # Get category
    res1 = cur.execute("SELECT * FROM terms order by term_id desc")

    db_terms = cur.fetchall()

    res2 = cur.execute("SELECT alias FROM terms order by term_id desc")
    db_terms_alias = cur.fetchall()

    # Get all parent category list
    parent_list = list(map(lambda i: (i['term_id'], i['name']), db_terms))
    parent_list.insert(0, [0, 'None'])

    # Populate (id, name) form fields
    form.parent.choices = parent_list

    # Get all name list
    alias_list = list(map(lambda i: i['alias'], db_terms_alias))

    # Add category
    if request.method == 'POST' and form.validate():
        name = form.name.data
        alias = form.alias.data
        description = form.description.data
        parent = request.form['parent']
        date_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if name.lower() not in alias_list:
            if alias not in alias_list:
                # Create Cursor
                cur = mysql.connection.cursor()

                # Insert user info
                cur.execute("INSERT INTO terms(name, alias, description, term_parent, date_update) VALUES(%s, %s, %s, %s, %s)",
                            (name, name.lower() if alias == '' else alias, description, parent, date_update))

                # Commit to DB
                mysql.connection.commit()

                flash('Category created.', 'success')

                # Close connection
                cur.close()

                return redirect(url_for('.admin_category'))
            else:
                flash("'%s' exists, please try another one." % alias, 'warning')
                return redirect(url_for('.admin_category'))
        else:
            # error = 'Category "%s" exists, please try another one.' % name
            # return render_template("admin/admin_category.html", form=form, error=error)
            flash("'%s' exists, please try another one." % name, 'warning')
            return redirect(url_for('.admin_category'))
    else:
        # List category
        # Create cursor
        cur = mysql.connection.cursor()

        # Get posts
        res1 = cur.execute(
            "SELECT t1.term_id, t1.name, t1.alias, t1.description, t1.date_update, t2.name AS parent FROM terms t1 LEFT JOIN terms t2 ON t1.term_parent = t2.term_id ORDER BY t1.term_id DESC")

        cate = cur.fetchall()

        # Each page size
        page_size = 15

        # Paginated category list
        cate_cut = list(paginate(cate, page_size))

        # Page number list
        cate_list = list(range(1, len(cate_cut) + 1))

        # Get posts count per each category 
        res2 = cur.execute("SELECT t.alias, (SELECT Count(p.post_title) FROM posts p WHERE p.post_parent=t.term_id) AS post_count FROM terms t")

        counts = cur.fetchall()

        # Close connection
        cur.close()

        if res1 > 0 and page > 0 and page < len(cate_cut) + 1:
            return render_template('admin/admin_category.html', cates=cate_cut[page - 1],
                                   page=page, page_list=cate_list, form=form, action=action, counts=counts)
        else:
            return redirect(url_for('.admin_category'))


# Edit post
@routes.route('/admin/edit_category/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_edit_category(id):
    action = 'Update category'
    # Get form
    form = CategoryForm(request.form)

    # Create cursor
    cur = mysql.connection.cursor()

    # Get category by id
    res1 = cur.execute("SELECT * FROM terms WHERE term_id = %s", [id])

    cates = cur.fetchone()

    # Get all category list
    res2 = cur.execute("SELECT * FROM terms order by term_id desc")

    cates_all = cur.fetchall()

    # Populate (id, name) form fields
    name_list = list(map(lambda i: (i['term_id'], i['name']), cates_all))

    cur.close()

    # Populate category form fields
    form.name.data = cates['name']
    form.alias.data = cates['alias']
    form.description.data = cates['description']
    form.parent.choices = name_list
    form.parent.process_data(cates['term_parent'])
    #form_id = cates['term_id']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        alias = request.form['alias']
        description = request.form['description']
        date_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        parent = request.form['parent']

        # Create Cursor
        cur = mysql.connection.cursor()
        # app.logger.info(title)
        # Execute
        cur.execute(
            "UPDATE terms SET name=%s, alias=%s, description=%s, date_update=%s, term_parent=%s WHERE term_id=%s", (name, alias, description, date_update, parent, id))
        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Category Updated.', 'success')

        return redirect(url_for('.admin_category'))

    return render_template('admin/admin_edit_category.html', form=form, action=action)


# Delete category
@routes.route('/admin/delete_category/<string:id>/', methods=['POST'])
@is_logged_in
@is_active
@is_admin
def admin_delete_category(id):
    if int(id)==1:
        flash('Default category can not be deleted.', 'warning')
        return redirect(url_for('.admin_category'))
    else:
        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("DELETE FROM terms WHERE term_id = %s", [id])

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Category Deleted.', 'success')

        return redirect(url_for('.admin_category'))


# Users entry
@routes.route('/admin/users/')
@routes.route('/admin/users/<int:page>/')
@is_logged_in
@is_active
@is_admin
def admin_users(page=1):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get posts
    result = cur.execute("SELECT u.id, u.username, u.fullname, u.email, u.register_date, u.user_status, r.role FROM users u LEFT JOIN roles r ON u.user_role = r.id ORDER BY u.id DESC")

    if result > 0:
        users = cur.fetchall()

        # Each page size
        page_size = 15

        # Paginated posts list
        users_cut = list(paginate(users, page_size))

        # Page number list
        page_list = list(range(1, len(users_cut) + 1))

        # Close connection
        cur.close()

        if page > 0 and page < len(users_cut) + 1:
            return render_template('admin/admin_users.html', users=users_cut[page - 1],
                                   page=page, page_list=page_list)
        else:
            return redirect(url_for('.admin_users'))


# User Form Class
class UserForm(Form):
    username = StringField('Username <span class="text-danger">*</span>', [validators.Regexp('\w+$', message="Name must contain only letters numbers or underscore"),
                                validators.Length(min=5, max=25)])
    fullname = StringField('Fullname <span class="text-danger">*</span>', [validators.Length(min=6, max=25)])
    password = PasswordField('Password <span class="text-danger">*</span>', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match'),
        validators.Length(min=6, max=25)
    ])
    confirm = PasswordField('Confirm Password <span class="text-danger">*</span>')
    email = EmailField('Email <span class="text-danger">*</span>', [validators.Length(
        min=6, max=50), validators.Email()])
    role = SelectField('role', coerce=int)
    description = TextAreaField(
        'Description', [validators.Length(min=0, max=200)])


# Add post
@routes.route('/admin/add_user/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_add_user():
    form = UserForm(request.form)
    # Create cursor
    cur = mysql.connection.cursor()

    # Get invitation code
    res1 = cur.execute("SELECT * FROM roles order by id ASC")

    db_roles = cur.fetchall()

    res2 = cur.execute("SELECT username FROM users order by id ASC")
    db_user = cur.fetchall()

    # Get all category list
    role_list = list(map(lambda i: (i['id'], i['role']), db_roles))

    # Populate (id, name) form fields
    form.role.choices = role_list

    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        fullname = form.fullname.data
        email = form.email.data
        role = form.role.data
        description = form.description.data

        # Create Cursor
        cur = mysql.connection.cursor()

        if username.lower() not in list(map(lambda i: i['username'], db_user)):
            # Execute
            cur.execute("INSERT INTO users(username, password, fullname, email, user_role, description) VALUES(%s, %s, %s, %s, %s, %s)",
                        (username, password, fullname, email, role, description))

            # Commit to DB
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash('User Created...', 'success')

            return redirect(url_for('.admin_users'))
        else:
            error = 'Username "%s" exists, please try another one.' % username
            return render_template('admin/admin_add_user.html', form=form, error=error)

    return render_template('admin/admin_add_user.html', form=form)


# Delete user
@routes.route('/admin/delete_user/<string:id>/', methods=['POST'])
@is_logged_in
@is_active
@is_admin
def admin_delete_user(id):
    if int(id)==1:
        flash('Default Admin can not be deleted.', 'warning')
        return redirect(url_for('.admin_users'))
    else:
        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("DELETE FROM users WHERE id = %s", [id])

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('User Deleted.', 'success')

        return redirect(url_for('.admin_users'))


# User Edit Form Class
class UserEditForm(Form):
    fullname = StringField('Fullname <span class="text-danger">*</span>', [validators.Length(min=5, max=25)])
    password = PasswordField('New Password', [
        validators.EqualTo('confirm', message='Passwords do not match'),
        validators.Length(min=0, max=25)
    ])
    confirm = PasswordField('Confirm New Password')
    email = EmailField('Email <span class="text-danger">*</span>', [validators.Length(
        min=6, max=50), validators.Email()])
    role = SelectField('Role', coerce=int)
    status = RadioField('User Status', coerce=int)
    description = TextAreaField(
        'Description', [validators.Length(min=0, max=200)])


# Edit post
@routes.route('/admin/edit_user/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_edit_user(id):
    # Get form
    form = UserEditForm(request.form)

    # Create cursor
    cur = mysql.connection.cursor()

    # Get user by id
    res1 = cur.execute("SELECT * FROM users WHERE id = %s", [id])

    db_user = cur.fetchone()

    # Get all roles list
    res2 = cur.execute("SELECT * FROM roles order by id ASC")

    db_roles = cur.fetchall()

    # Populate (id, role) form fields
    role_list = list(map(lambda i: (i['id'], i['role']), db_roles))

    # Populate user_status form fields
    status_list = [(1, 'active'), (0, 'inactive')]

    cur.close()

    # Populate users form fields
    form.fullname.data = db_user['fullname']
    form.email.data = db_user['email']
    form.description.data = db_user['description']
    form.role.choices = role_list
    form.role.process_data(db_user['user_role'])
    form.status.choices = status_list
    form.status.process_data(db_user['user_status'])

    if request.method == 'POST' and form.validate():
        password = sha256_crypt.encrypt(str(form.password.data))
        fullname = request.form['fullname']
        email = request.form['email']
        role = request.form['role']
        status = request.form['status']
        description = request.form['description']

        # Create Cursor
        cur = mysql.connection.cursor()
        # app.logger.info(title)
        # Execute
        if form.password.data == "":
             cur.execute(
            "UPDATE users SET fullname=%s, email=%s, description=%s, user_role=%s, user_status=%s WHERE id=%s", (fullname, email, description, role, status, id))
        else:
            cur.execute(
            "UPDATE users SET fullname=%s, password=%s, email=%s, description=%s, user_role=%s, user_status=%s WHERE id=%s", (fullname, password, email, description, role, status, id))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('User Updated.', 'success')

        return redirect(url_for('.admin_users'))

    return render_template('admin/admin_edit_user.html', form=form, db_user=db_user)


# Invitation Form Class
class InviteForm(Form):
    code = StringField('Invitation Code', [validators.Length(min=0, max=50)])


# Invitation entry
@routes.route('/admin/invite/', methods=['GET', 'POST'])
@routes.route('/admin/invite/<int:page>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_invite(page=1):
    form = InviteForm(request.form)

    # Create cursor
    cur = mysql.connection.cursor()

    # Get invitation
    res1 = cur.execute("SELECT * FROM invitation order by id desc")

    db_invite = cur.fetchall()

    invite_list = list(map(lambda i: i['code'], db_invite))

    # Add invitation
    if request.method == 'POST' and form.validate():
        code = form.code.data

        if code not in invite_list:
            # Create Cursor
            cur = mysql.connection.cursor()

            # Insert user info
            cur.execute("INSERT INTO invitation(code) VALUES(%s)", (code,))

            # Commit to DB
            mysql.connection.commit()

            flash('Invitation code created.', 'success')

            # Close connection
            cur.close()

            return redirect(url_for('.admin_invite'))
        else:
            flash("'%s' exists, please try another one." % code, 'warning')
            return redirect(url_for('.admin_invite'))
    else:
        # List invitation code
        # Create cursor
        cur = mysql.connection.cursor()

        # Get posts
        res1 = cur.execute("SELECT id, code FROM invitation")

        db_invite = cur.fetchall()

        # Each page size
        page_size = 10

        # Paginated Invitation list
        inv_cut = list(paginate(db_invite, page_size))

        # Page number list
        inv_list = list(range(1, len(inv_cut) + 1))

        # Close connection
        cur.close()

        if res1 > 0 and page > 0 and page < len(inv_cut) + 1:
            return render_template('admin/admin_invite.html', invite=inv_cut[page - 1],
                                   page=page, page_list=inv_list, form=form)
        else:
            return redirect(url_for('.admin_invite'))


# Delete invite
@routes.route('/admin/delete_invite/<string:id>/', methods=['POST'])
@is_logged_in
@is_active
@is_admin
def admin_delete_invite(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM invitation WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Invitation Deleted.', 'success')

    return redirect(url_for('.admin_invite'))


# Comments entry
@routes.route('/admin/comments/')
@routes.route('/admin/comments/<int:page>/')
@is_logged_in
@is_active
@is_admin
def admin_comments(page=1):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get posts
    result = cur.execute("SELECT c.id, c.comm_author, c.comm_content, c.comm_date, c.comm_modified, c.comm_post, p.post_title FROM comments c, posts p WHERE c.comm_post = p.id ORDER BY c.id DESC")
    comments = cur.fetchall()

    if result > 0:
        # Each page size
        page_size = 15

        # Paginated posts list
        comments_cut = list(paginate(comments, page_size))

        # Page number list
        page_list = list(range(1, len(comments_cut) + 1))

        # Close connection
        cur.close()

        if page > 0 and page < len(comments_cut) + 1:
            return render_template('admin/admin_comments.html', comments=comments_cut[page - 1],
                                   page=page, page_list=page_list)
        else:
            return redirect(url_for('.admin_comments'))
    else:
        msg = 'No comments Found.'
        comments = ''
        page_list = [1]
        return render_template('admin/admin_comments.html', comments=comments,
                                page=page, page_list=page_list, msg=msg)


# Comment Edit Form Class
class CommEditForm(Form):
    comment = TextAreaField('', [validators.Length(min=10)])


# Edit comment
@routes.route('/admin/edit_comment/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_edit_comment(id):
    # Get form
    form = CommEditForm(request.form)

    # Create cursor
    cur = mysql.connection.cursor()

    # Get user by id
    res1 = cur.execute("SELECT * FROM comments WHERE id = %s", [id])

    db_comment = cur.fetchone()

    cur.close()

    # Populate comment form fields
    form.comment.data = db_comment['comm_content']

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

        return redirect(url_for('.admin_comments'))

    return render_template('admin/admin_edit_comment.html', form=form, db_comment=db_comment)


# Delete comment
@routes.route('/admin/delete_comment/<string:id>/', methods=['POST'])
@is_logged_in
@is_active
@is_admin
def admin_delete_comment(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM comments WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Comment Deleted.', 'success')

    return redirect(url_for('.admin_comments'))


# General Setting Form Class
class SettingForm(Form):
    siteurl = StringField('Site URL', [validators.Length(min=0, max=100)])
    home = StringField('Home', [validators.Length(min=0, max=100)])
    bloghome = StringField('Blog Home', [validators.Length(min=0, max=100)])
    blogdescription = TextAreaField(
        'Blog Description', [validators.Length(min=0, max=200)])
    adminemail = EmailField('Admin Email', [validators.Length(
        min=6, max=50), validators.Email()])
    register = RadioField('User Can Register', coerce=int)


# Edit post
@routes.route('/admin/setting/', methods=['GET', 'POST'])
@is_logged_in
@is_active
@is_admin
def admin_setting():
    # Get form
    form = SettingForm(request.form)

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

    # Populate user_status form fields
    register_list = [(1, 'Yes'), (0, 'No')]

    cur.close()

    # Populate setting form fields
    form.siteurl.data = field_dict['siteurl']
    form.home.data = field_dict['home']
    form.bloghome.data = field_dict['bloghome']
    form.blogdescription.data = field_dict['blogdescription']
    form.adminemail.data = field_dict['admin_email']
    form.register.choices = register_list
    form.register.process_data(field_dict['users_can_register'])


    if request.method == 'POST' and form.validate():
        siteurl = request.form['siteurl']
        home = request.form['home']
        bloghome = request.form['bloghome']
        blogdescription = request.form['blogdescription']
        adminemail = request.form['adminemail']
        register = request.form['register']

        form_dict = {'siteurl': siteurl,
                    'home': home,
                    'bloghome': bloghome,
                    'blogdescription': blogdescription,
                    'admin_email': adminemail,
                    'users_can_register': register}

        # Create Cursor
        cur = mysql.connection.cursor()

        for key, val in form_dict.items():
            cur.execute(
                "UPDATE options SET option_value=%s WHERE option_name=%s", (val, key))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Setting Updated.', 'success')

        return redirect(url_for('.admin_setting'))

    return render_template('admin/admin_setting.html', form=form, db_options=db_options)