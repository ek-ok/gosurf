from gosurf import application
from gevent import monkey


if __name__ == '__main__':
    monkey.patch_all()
    application.run(debug=True, host='0.0.0.0')
