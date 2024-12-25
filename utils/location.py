import requests


class APIQuotaExceededError(Exception):
    pass


class Location:
    def __init__(self, accuweather_api_key: str, yandex_api_key: str):
        self.yandex_key = yandex_api_key
        self.accuweather_key = accuweather_api_key

    def _request_to_yandex(self, city: str) -> dict:
        params = {
            'apikey': self.yandex_key,
            'geocode': city,
            'lang': 'ru_RU',
            'format': 'json'
        }
        response = requests.get('https://geocode-maps.yandex.ru/1.x', params=params)
        response.raise_for_status()
        return response.json()

    def get_coordinates(self, city: str) -> tuple:
        data = self._request_to_yandex(city)
        try:
            coords = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
            lon, lat = map(float, coords.split(' '))
            return lat, lon
        except (IndexError, KeyError) as e:
            raise ValueError(f"Ошибка получения координат для города '{city}': {e}")

    def get_location_key(self, lat: float, lon: float) -> str:
        params = {
            'apikey': self.accuweather_key,
            'q': f'{lat},{lon}'
        }
        response = requests.get('https://dataservice.accuweather.com/locations/v1/cities/geoposition/search',
                                params=params)

        if response.status_code == 503:
            raise APIQuotaExceededError("Запросы к API закончились")
        elif response.status_code in (200, 201):
            return response.json()['Key']

        raise Exception(f'Ошибка при получении данных. Код ошибки: {response.status_code}')
