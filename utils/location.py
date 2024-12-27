import requests


class APIQuotaExceededError(Exception):
    pass


class Location:
    def __init__(self, accuweather_api_key):
        self.accuweather_key = accuweather_api_key

    def get_location_key_lat_lon(self, city):
        try:
            location_url = f"https://dataservice.accuweather.com/locations/v1/cities/search?"
            params = {
                "apikey": self.accuweather_key,
                "language": "ru",
                "q": city,
                "metric": "true",
            }
            response = requests.get(location_url, params=params)
            data = response.json()
            print("lat:", data[0]['GeoPosition']['Latitude'])
            print("lom:", data[0]['GeoPosition']['Longitude'])

            return data[0]["Key"], data[0]['GeoPosition']['Latitude'], data[0]['GeoPosition']['Longitude']
        except APIQuotaExceededError as e:
            print(f"Обработка APIQuotaExceededError: {e}")
            raise
        except KeyError as e:
            raise Exception(f"Ошибка получения ключа локации: {e}")
        except Exception as e:
            raise Exception(f"Ошибка запроса к API AccuWeather: {e}")

    def get_location_key(self, lat: float, lon: float) -> str:
        try:
            params = {
                'apikey': self.accuweather_key,
                'q': f'{lat},{lon}'
            }
            response = requests.get('https://dataservice.accuweather.com/locations/v1/cities/geoposition/search',
                                    params=params)

            if response.status_code == 503:
                raise APIQuotaExceededError("Запросы к API закончились")
            return response.json()['Key']
        except Exception as e:
            raise Exception(f'Ошибка при получении данных. Код ошибки: {response.status_code}')
