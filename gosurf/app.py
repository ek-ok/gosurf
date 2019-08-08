import json
import time
from datetime import datetime

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

app = Flask(__name__)


@app.route('/')
def index():
    conditions = fetch_conditions(days=3)
    days, spots = parse_conditions(conditions)
    return render_template('index.html', days=days, spots=spots)


def fetch_conditions(days):
    attempts = 0
    max_attempts = 3
    rs = (grequests.get(URL.format(_id, days)) for _id in SPOTS._id)
    while attempts < max_attempts:
        try:
            print(attempts)
            results = grequests.map(rs)
            return [json.loads(r.text)['data']['conditions'] for r in results]
        except (AttributeError, KeyError, json.decoder.JSONDecodeError):
            attempts += 1
            # time.sleep(1)


def parse_conditions(data):
    forecast_list = []
    for _id, spot_data in zip(SPOTS._id, data):
        for forecast in spot_data:
            dt = datetime.fromtimestamp(forecast['timestamp'])
            am = ID_TO_SCORE[forecast['am']['rating']]['score']
            pm = ID_TO_SCORE[forecast['pm']['rating']]['score']
            score = round((am + pm) / 2)
            forecast_list.append({'_id': _id, 'date': dt, 'score': score})

    forecasts = (pd.DataFrame(forecast_list)
                   .pivot_table(index='_id', values='score', columns='date'))

    days = [dt.strftime('%a %-m/%-d') for dt in forecasts.columns]

    forecasts = forecasts.apply(
        lambda x: [{**{'score': i}, **SCORE_TO_ID[round(i)]} for i in x], axis=1)
    forecasts = forecasts.rename('forecasts').reset_index()
    spots = pd.merge(SPOTS, forecasts, on='_id').drop(columns='_id')
    spot_dict = spots.to_dict('records')

    return days, spot_dict


if __name__ == '__main__':
    # app.jinja_env.globals.update(zip=zip)
    app.run(debug=True, host='0.0.0.0')
