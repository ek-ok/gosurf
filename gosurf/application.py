from flask import Flask, render_template
from gevent import monkey

from surfline import SurfLine


class SurfApp(Flask):
    def __init__(self, *args, **kwargs):
        super(SurfApp, self).__init__(*args, **kwargs)
        self.surfline = SurfLine()


application = SurfApp(__name__)


@application.route('/')
def index():
    """Renter the index page back to front end"""
    days, spots = application.surfline.get_conditions()
    return render_template('index.html', days=days, spots=spots)


if __name__ == '__main__':
    monkey.patch_all()
    application.run(host='0.0.0.0')
