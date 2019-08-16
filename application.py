from gevent import monkey

from gosurf import application


if __name__ == '__main__':
    monkey.patch_all()
    application.run(host='0.0.0.0')
