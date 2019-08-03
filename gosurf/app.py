import json
from datetime import datetime

import grequests
import pandas as pd
from flask import Flask, render_template


app = Flask(__name__)


@app.route('/')
def home():
    days, spots = surfline_api(days=3)
    return render_template('index.html', days=days, spots=spots)


def surfline_api(days=3):
    condition_to_num = {
        None: 0,
        'FLAT': 1,
        'VERY_POOR': 2,
        'POOR': 3,
        'POOR_TO_FAIR': 4,
        'FAIR': 5,
        'FAIR_TO_GOOD': 6,
        'GOOD': 7,
        'VERY_GOOD': 8,
        'GOOD_TO_EPIC': 9,
        'EPIC': 10
    }
    url = "http://services.surfline.com/kbyg/spots/forecasts/conditions?spotId={}&days={}"

    locations = pd.read_csv('static/locations.csv')

    # Surfline API
    rs = (grequests.get(url.format(_id, days)) for _id in locations._id)
    results = grequests.map(rs)

    forecast_list = []
    for _id, result in zip(locations._id, results):
        j = json.loads(result.text)['data']['conditions']
        for day in j:
            dt = datetime.fromtimestamp(day['timestamp'])
            am, pm = day['am']['rating'], day['pm']['rating']
            score = (condition_to_num[am] + condition_to_num[pm]) / 2 * 10
            forecast_list.append({'_id': _id, 'date': dt, 'score': int(score)})

    forecasts = pd.DataFrame(forecast_list)
    forecasts = forecasts.pivot_table(index='_id', values='score',
                                      columns='date')

    days = [dt.strftime('%a %-m/%-d') for dt in forecasts.columns]
    forecasts = (forecasts.apply(lambda x: list(x), axis=1)
                          .rename('scores')
                          .reset_index())

    spots = pd.merge(locations, forecasts, on='_id').drop(columns='_id')
    spot_dict = spots.to_dict('records')

    return days, spot_dict


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
