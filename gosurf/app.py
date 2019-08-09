from flask import Flask, render_template
from gevent import monkey

from surfline import SurfLine


class SurfApp(Flask):
    def __init__(self, *args, **kwargs):
        super(SurfApp, self).__init__(*args, **kwargs)
        self.surfline = SurfLine()


app = SurfApp(__name__)


@app.route('/')
def index():
    """Renter the index page back to front end"""
    days, spots = app.surfline.get_conditions()
    return render_template('index.html', days=days, spots=spots)


if __name__ == '__main__':
    monkey.patch_all()
    app.run(debug=True, host='0.0.0.0')
