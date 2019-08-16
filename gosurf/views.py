from flask import Flask, render_template
from gevent import monkey

from .surfline import SurfLine


application = SurfApp(__name__)
monkey.patch_all()


class SurfApp(Flask):
    def __init__(self, *args, **kwargs):
        super(SurfApp, self).__init__(*args, **kwargs)
        self.surfline = SurfLine()


@application.route('/')
def index():
    """Renter the index page back to front end"""
    days, spots = application.surfline.get_conditions()
    return render_template('index.html', days=days, spots=spots)
