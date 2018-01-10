# FlaskApp

Simple application with frontend/backend authentication and Blog orchestration using the Python Flask micro-framework

## Prerequisite

To use this template, your computer needs:

- [Python 3](https://python.org)
- [Pip Package Manager](https://pypi.python.org/pypi)
- [Nginx](https://nginx.org/en/)
- [Uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/)
- [MySQL](https://www.mysql.com/)
- [Python3+Flask+nWSGI+Nginx integration](http://www.showerlee.com/archives/2024)

## Installation

```bash
git@github.com:showerlee/Flaskdev.git
```

```bash
cd Flaskdev
```

```bash
virtualenv -p /usr/bin/python3 .py3env
```

```bash
source .py3env/bin/activate
```

```bash
pip install flask Flask-login Flask-Mail pygal flask_mysqldb flask-mysql Flask-WTF passlib uwsgi requests
```

```bash
mysql -uroot -p"Your mysql root password" flaskdev < flaskdev.sql
```

```bash
/etc/init.d/nginx start && /etc/uwsgi/bin/uwsgi.sh start
```
## Admin Login
user/pass: flaskadmin/flaskadmin