import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, ALL
from dash import dash_table
from dotenv import load_dotenv

from utils.location import Location
from utils.weather import Weather

env_path = Path("venv") / ".env"
load_dotenv(dotenv_path=env_path)


class APIQuotaExceededError(Exception):
    pass


ACCUWEATHER_API_KEY = os.getenv('ACCUWEATHER_API_KEY')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')

app = Dash(__name__)

location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)

app.layout = html.Div([
    html.H1("Прогноз погоды"),
    html.Div([
        html.Label("Введите города маршрута:"),
        html.Div([dcc.Input(id={"type": "city-input", "index": 0}, type="text", placeholder="Город №1")],
                 id="city-input-container"),
        html.Button("Добавить город в маршрут", id="add-city", n_clicks=0),
    ]),
    html.Div([
        html.Label("Выберите, на сколько дней построить прогноз:"),
        dcc.Dropdown(
            id="forecast-days",
            options=[{"label": f"{i} {'день' if i == 1 else 'дня'}", "value": i} for i in range(1, 6)],
            value=1,
        ),
    ]),
    html.Button("Получить прогноз", id="submit-button", n_clicks=0),
    html.Div(id="output-container"),
])


@app.callback(
    Output("city-input-container", "children"),
    Input("add-city", "n_clicks"),
    State("city-input-container", "children"),
)
def add_city_input(n_clicks, children):
    new_input = dcc.Input(id={"type": "city-input", "index": n_clicks}, type="text",
                          placeholder=f"Город №{n_clicks + 2}")
    return children + [new_input]


@app.callback(
    Output("output-container", "children"),
    Input("submit-button", "n_clicks"),
    State({"type": "city-input", "index": ALL}, "value"),
    State("forecast-days", "value"),
)
def update_output(n_clicks, cities, forecast_days):
    if n_clicks > 0:
        all_cities = [city for city in cities if city]
        if not all_cities:
            return html.Div("Должен быть введен хотя бы один город")
        if any(char.isdigit() for city in all_cities for char in city):
            return html.Div("В названии городов не должны присутствовать цифры")

        weather_data, city_coordinates, errors = fetch_weather_data(all_cities, forecast_days)

        output_children = []
        if errors:
            output_children.append(html.Div(errors))

        output_children.append(generate_weather_map(city_coordinates))

        for city, data in weather_data.items():
            output_children.extend(generate_weather_figures(city, data["forecast"], forecast_days))

        output_children.append(generate_weather_table(weather_data, forecast_days))

        return output_children

    return html.Div()


def fetch_weather_data(cities, forecast_days):
    weather_data = {}
    city_coordinates = []
    errors = []

    for city in cities:
        try:
            lat, lon = location.get_coordinates(city)
            location_key = location.get_location_key(lat, lon)
            if not location_key:
                errors.append(f"Не удалось найти город <<{city}>>")
                continue
            forecast = weather.get_forecast_data_request(location_key, days=forecast_days)
            if not forecast:
                errors.append(f"Не удалось получить прогноз для города <<{city}>>")
                continue
            weather_data[city] = {"forecast": forecast, "latitude": lat, "longitude": lon}
            city_coordinates.append({"city": city, "lat": lat, "lon": lon})
        except APIQuotaExceededError:
            errors.append(f"Превышена квота запросов для API по городу <<{city}>>")
        except Exception as excep:
            errors.append(f"Ошибка обработки города <<{city}>>: {str(excep)}")

    return weather_data, city_coordinates, errors


def generate_weather_map(city_coordinates):
    df_city_coordinates = pd.DataFrame(city_coordinates)
    fig = go.Figure(go.Scattermapbox(
        lat=df_city_coordinates["lat"],
        lon=df_city_coordinates["lon"],
        mode="markers+lines",
        marker=go.scattermapbox.Marker(size=9),
        text=df_city_coordinates["city"],
    ))
    fig.update_layout(mapbox_style="open-street-map", mapbox_zoom=3,
                      mapbox_center_lat=df_city_coordinates["lat"].mean(),
                      mapbox_center_lon=df_city_coordinates["lon"].mean(), height=500)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return dcc.Graph(figure=fig)


def generate_weather_figures(city, forecast, forecast_days):
    figures = []
    dates, min_temps, max_temps, wind_speeds, precipitation_probs = [], [], [], [], []

    for cnt, day in enumerate(forecast["DailyForecasts"]):
        if cnt >= forecast_days:
            break
        dates.append(day["Date"][:10])
        min_temps.append(day["Temperature"]["Minimum"]["Value"])
        max_temps.append(day["Temperature"]["Maximum"]["Value"])
        wind_speeds.append(day["Day"]["Wind"]["Speed"]["Value"])
        precipitation_probs.append(day["Day"]["PrecipitationProbability"])

    figures.append(create_temperature_fig(city, dates, min_temps, max_temps))
    figures.append(create_wind_fig(city, dates, wind_speeds))
    figures.append(create_precipitation_fig(city, dates, precipitation_probs))

    return figures


def create_temperature_fig(city, dates, min_temps, max_temps):
    return dcc.Graph(figure=go.Figure(data=[
        go.Scatter(x=dates, y=min_temps, mode="lines+markers", name="Мин. температура"),
        go.Scatter(x=dates, y=max_temps, mode="lines+markers", name="Макс. температура")
    ], layout=go.Layout(title=f"Температура в городе '{city}'", xaxis={"title": "Дата"},
                        yaxis={"title": "Температура (°C)"})))


def create_wind_fig(city, dates, wind_speeds):
    return dcc.Graph(figure=go.Figure(data=[go.Bar(x=dates, y=wind_speeds, name="Скорость ветра")],
                                      layout=go.Layout(title=f"Скорость ветра в городе '{city}'",
                                                       xaxis={"title": "Дата"},
                                                       yaxis={"title": "Скорость ветра (км/ч)"})))


def create_precipitation_fig(city, dates, precipitation_probs):
    return dcc.Graph(figure=go.Figure(data=[go.Bar(x=dates, y=precipitation_probs, name="Вероятность осадков")],
                                      layout=go.Layout(title=f"Вероятность дождя в городе '{city}'",
                                                       xaxis={"title": "Дата"}, yaxis={"title": "Вероятность (%)"})))


def generate_weather_table(weather_data, forecast_days):
    table_data = []
    for city, data in weather_data.items():
        forecast = data["forecast"]
        for cnt, day in enumerate(forecast["DailyForecasts"]):
            if cnt >= forecast_days:
                break
            table_data.append({
                "Город": city,
                "Дата": day["Date"][:10],
                "Мин. температура (°C)": day["Temperature"]["Minimum"]["Value"],
                "Макс. температура (°C)": day["Temperature"]["Maximum"]["Value"],
                "Скорость ветра (км/ч)": day["Day"]["Wind"]["Speed"]["Value"],
                "Вероятность осадков (%)": day["Day"]["PrecipitationProbability"]
            })

    return dash_table.DataTable(
        id='weather-table',
        columns=[{"name": col_name, "id": col_name} for col_name in
                 ["Город", "Дата", "Мин. температура (°C)", "Макс. температура (°C)", "Скорость ветра (км/ч)",
                  "Вероятность осадков (%)"]],
        data=table_data,
        style_table={'height': '400px', 'overflowY': 'auto'},
        style_cell={'textAlign': 'center', 'padding': '5px'},
        style_header={'fontWeight': 'bold', 'textAlign': 'center'},
    )


if __name__ == "__main__":
    app.run_server(debug=True)