import decimal
import json
import os
from datetime import datetime

import grequests
import pandas as pd
import yaml
from gevent import monkey
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.utils import urlparse


monkey.patch_all()


def roundup(n):
    """In Python 3 round(0.5) is 0. This function returns 1"""
    return int(decimal.Decimal(n).quantize(decimal.Decimal('1'),
                                           rounding=decimal.ROUND_HALF_UP))


def parse_url_params(url):
    """Parses params from an URL"""
    params = dict(x.split('=') for x in urlparse(url).query.split('&'))
    return params['spotId']


class SurfLine(object):
    def __init__(self, retry=3):
        here = os.path.dirname(os.path.abspath(__file__))
        self.retry = retry
        self.url = "http://services.surfline.com/kbyg/spots/forecasts/conditions?spotId={}&days={}"
        self.session = self._create_session()
        self.spots = pd.read_csv(os.path.join(here,'static/spots.csv'))

        with open(os.path.join(here,'static/conditions.yaml')) as f:
            condition_map = yaml.safe_load(f)
            self.score_to_id = condition_map['score_to_id']
            self.id_to_score = condition_map['id_to_score']

    def _create_session(self):
        retries = Retry(total=self.retry, status_forcelist=[500, 502, 503, 504])
        s = Session()
        s.mount('http://', HTTPAdapter(max_retries=retries))
        return s

    def _fetch_conditions(self, days):
        """Call Surfline API to request conditions"""
        reqs = (grequests.get(self.url.format(_id, days), session=self.session)
                for _id in self.spots._id)
        results = grequests.map(reqs)

        return [(parse_url_params(r.request.url), json.loads(r.text)['data']['conditions'])
                for r in results]

    def _parse_conditions(self, data):
        """Parse conditions from a JSON and take an average of AM and PM"""
        forecast_list = []
        for _id, spot_data in data:
            for forecast in spot_data:
                score = roundup((self.id_to_score[forecast['am']['rating']] +
                                 self.id_to_score[forecast['pm']['rating']]) / 2)

                forecast_list.append({'_id': _id,
                                      'date': forecast['timestamp'],
                                      'score': score})

        forecasts = (pd.DataFrame(forecast_list)
                       .pivot_table(index='_id', values='score', columns='date'))
        days = [datetime.fromtimestamp(d).strftime('%a %-m/%-d') for d in forecasts.columns]

        forecasts = forecasts.apply(
            lambda x: [{**{'score': i}, **self.score_to_id[round(i)]} for i in x], axis=1)
        forecasts = forecasts.rename('forecasts').reset_index()
        spots = pd.merge(self.spots, forecasts, on='_id').drop(columns='_id')
        spot_dict = spots.to_dict('records')

        return days, spot_dict

    def get_conditions(self, days=6):
        conditions = self._fetch_conditions(days)
        days, spots = self._parse_conditions(conditions)
        return days, spots
