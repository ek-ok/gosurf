import json
from datetime import datetime
import decimal

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.utils import urlparse

import grequests
import pandas as pd
import yaml
from flask import Flask, render_template


URL = "http://services.surfline.com/kbyg/spots/forecasts/conditions?spotId={}&days={}"
SPOTS = pd.read_csv('static/spots.csv')

with open('static/conditions.yaml') as f:
    CONDITION_MAP = yaml.safe_load(f)
    SCORE_TO_ID = CONDITION_MAP['score_to_id']
    ID_TO_SCORE = CONDITION_MAP['id_to_score']
print(ID_TO_SCORE)
app = Flask(__name__)


@app.route('/')
def index():
    conditions = fetch_conditions(days=6)
    days, spots = parse_conditions(conditions)
    return render_template('index.html', days=days, spots=spots)


def fetch_conditions(days):
    retry = Retry(total=3, status_forcelist=[500, 502, 503, 504])
    s = Session()
    s.mount('http://', HTTPAdapter(max_retries=retry))
    reqs = (grequests.get(URL.format(_id, days), session=s) for _id in SPOTS._id)
    results = grequests.map(reqs)

    return [(parse_url_params(r.request.url),
             json.loads(r.text)['data']['conditions']) for r in results]


def roundup(n):
    """In Python 3 round(0.5) is 0. This function returns 1"""
    return int(decimal.Decimal(n).quantize(decimal.Decimal('1'),
                                           rounding=decimal.ROUND_HALF_UP))


def parse_url_params(url):
    params = dict(x.split('=') for x in urlparse(url).query.split('&'))
    return params['spotId']


def parse_conditions(data):
    forecast_list = []
    for _id, spot_data in data:
        for forecast in spot_data:
            score = roundup((ID_TO_SCORE[forecast['am']['rating']] +
                             ID_TO_SCORE[forecast['pm']['rating']]) / 2)

            print(_id, score, forecast['am']['rating'], forecast['pm']['rating'])
            forecast_list.append({'_id': _id,
                                  'date': forecast['timestamp'],
                                  'score': score})

    forecasts = (pd.DataFrame(forecast_list)
                   .pivot_table(index='_id', values='score', columns='date'))
    days = [datetime.fromtimestamp(d).strftime('%a %-m/%-d') for d in forecasts.columns]

    forecasts = forecasts.apply(
        lambda x: [{**{'score': i}, **SCORE_TO_ID[round(i)]} for i in x], axis=1)
    forecasts = forecasts.rename('forecasts').reset_index()
    spots = pd.merge(SPOTS, forecasts, on='_id').drop(columns='_id')
    spot_dict = spots.to_dict('records')

    return days, spot_dict


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()
    app.run(debug=True, host='0.0.0.0')
