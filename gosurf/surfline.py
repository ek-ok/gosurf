import decimal
from datetime import datetime
import json
import os

import pandas as pd
import yaml
import requests


def roundup(n):
    """In Python 3 round(0.5) is 0. This function returns 1"""
    return int(decimal.Decimal(n).quantize(decimal.Decimal('1'),
                                           rounding=decimal.ROUND_HALF_UP))


def timestamp_to_strftime(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    return '{} {}'.format(dt.strftime('%a')[0], dt.strftime('%-d'))


class SurfLine(object):
    def __init__(self, retry=3):
        self.url = 'https://y36qk3xd7h.execute-api.us-east-1.amazonaws.com/default/surfline-api'
        here = os.path.dirname(os.path.abspath(__file__))
        self.spots = pd.read_csv(os.path.join(here, 'static/spots.csv'))
        with open(os.path.join(here, 'static/conditions.yaml')) as f:
            condition_map = yaml.safe_load(f)
            self.score_to_id = condition_map['score_to_id']
            self.id_to_score = condition_map['id_to_score']

    def _fetch_conditions(self, spot_ids, days):
        """Call Surfline API to request conditions"""
        r = requests.get(self.url, params={'spotId': spot_ids, 'days': days})
        return json.loads(r.text)

    def _parse_conditions(self, data):
        """Parse conditions from a JSON and take an average of AM and PM"""
        forecast_list = []
        for _id, spot_data in data.items():
            for forecast in spot_data:
                score = roundup((self.id_to_score[forecast['am']['rating']] +
                                 self.id_to_score[forecast['pm']['rating']]) / 2)

                forecast_list.append({'_id': _id,
                                      'date': forecast['timestamp'],
                                      'score': score})

        forecasts = (pd.DataFrame(forecast_list)
                     .pivot_table(index='_id', values='score', columns='date'))
        days = [timestamp_to_strftime(d) for d in forecasts.columns]

        forecasts = forecasts.apply(
            lambda x: [{**{'score': i}, **self.score_to_id[round(i)]} for i in x], axis=1)
        forecasts = forecasts.rename('forecasts').reset_index()
        spots = pd.merge(self.spots, forecasts, on='_id').drop(columns='_id')
        spot_dict = spots.to_dict('records')

        return days, spot_dict

    def get_conditions(self, spot_ids=None, days=6):
        spot_ids = spot_ids if spot_ids else self.spots._id.tolist()

        conditions = self._fetch_conditions(spot_ids, days)
        days, spots = self._parse_conditions(conditions)
        return days, spots
