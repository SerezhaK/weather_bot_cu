import requests


class Weather:
    def __init__(self, accuweather_api_key: str):
        self.accuweather_key = accuweather_api_key

    def get_forecast_data(self, location_key: str, days: int = 5) -> dict:
        forecast_url = f"https://dataservice.accuweather.com/forecasts/v1/daily/{days}day/{location_key}"
        params = {
            "apikey": self.accuweather_key,
            "language": "ru",
            "details": "true",
            "metric": "true",
        }

        response = requests.get(forecast_url, params=params)

        response.raise_for_status()  # Raise an HTTPError if the response was unsuccessful
        return response.json()