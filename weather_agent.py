from __future__ import annotations as _annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, List

import logfire
from devtools import debug
from httpx import AsyncClient

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import ModelMessage

from dotenv import load_dotenv
import aiohttp
from typing import TypedDict, Literal


load_dotenv()

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(
    send_to_logfire='if-token-present')


@dataclass
class Deps:
    client: AsyncClient
    weather_api_key: str | None
    geo_api_key: str | None


weather_agent = Agent(
    'openai:gpt-4o',
    # 'Be concise, reply with one sentence.' is enough for some models (like openai) to use
    # the below tools appropriately, but others like anthropic and gemini require a bit more direction.
    system_prompt=(
        'Be concise, reply with one sentence. Always include temperature in your response.'
    ),
    deps_type=Deps,
    retries=2,
)


@weather_agent.tool
async def get_lat_lng(
    ctx: RunContext[Deps], location_description: str
) -> dict[str, float]:
    """Get the latitude and longitude of a location.

    Args:
        ctx: The context.
        location_description: A description of a location.
    """
    if ctx.deps.geo_api_key is None:
        # if no API key is provided, return a dummy response (London)
        return {'lat': 51.1, 'lng': -0.1}

    params = {
        'q': location_description,
        'api_key': ctx.deps.geo_api_key,
    }
    with logfire.span('calling geocode API', params=params) as span:
        r = await ctx.deps.client.get('https://geocode.maps.co/search', params=params)
        r.raise_for_status()
        data = r.json()
        span.set_attribute('response', data)

    if data:
        return {'lat': data[0]['lat'], 'lng': data[0]['lon']}
    else:
        raise ModelRetry('Could not find the location')


@weather_agent.tool
async def get_weather(ctx: RunContext[Deps], lat: float, lng: float) -> dict[str, Any]:
    """Get the weather at a location. temperature attribute in response has the correct temperature

    Args:
        ctx: The context.
        lat: Latitude of the location.
        lng: Longitude of the location.

    """
    if ctx.deps.weather_api_key is None:
        # if no API key is provided, return a dummy response
        return {'temperature': '21 °C', 'description': 'Sunny'}
    
    params = {
        'apikey': ctx.deps.weather_api_key,
        'location': f'{lat},{lng}',
        'units': 'metric',
    }
    with logfire.span('calling weather API', params=params) as span:
        r = await ctx.deps.client.get(
            'https://api.tomorrow.io/v4/weather/realtime', params=params
        )
        r.raise_for_status()
        data = r.json()
        span.set_attribute('response', data)

    values = data['data']['values']

    return {
        'temperature': f'{values["temperature"]:0.0f}°C',
        'description': get_weather_description(values['weatherCode'])
    }

class WeatherData(TypedDict):
    temperature: str
    description: str

class ForecastData(TypedDict):
    hourly: list[WeatherData]
    location: str

@weather_agent.tool
async def get_forecast(ctx: RunContext[Deps], lat: float, lng: float) -> ForecastData:
    """Get hourly weather forecast at a location for the next five days.

    Args:
        ctx: The context.
        lat: Latitude of the location (-90 to 90).
        lng: Longitude of the location (-180 to 180).

    Returns:
        ForecastData with fields:
        - hourly: List of WeatherData for each hour
        - location: Location name from the API
    """
   
    params = {
        'apikey': ctx.deps.weather_api_key,
        'location': f'{lat},{lng}',
        'units': 'metric',
    }

    with logfire.span('calling forecast API', params=params) as span:
        r = await ctx.deps.client.get(
            'https://api.tomorrow.io/v4/weather/forecast', params=params
            )

        r.raise_for_status()
        data = r.json()
        span.set_attribute('response', data)

    hourly_data = []
    for interval in data['timelines']['hourly']: 
        values = interval['values']
        description = get_weather_description(values['weatherCode'])
        hourly_data.append({
            'date_time': interval['time'],
            'temperature': f"{values['temperature']:0.0f}°C",
            'description': description,
        })

    location = data.get('location', {}).get('name', 'Unknown')

    return {
        'hourly': hourly_data,
        'location': location
    }

def get_weather_description(code: int) -> str:
    """Get human-readable weather description from code."""
    return {
        1000: 'Clear, Sunny',
        1100: 'Mostly Clear',
        1101: 'Partly Cloudy',
        1102: 'Mostly Cloudy',
        1001: 'Cloudy',
        2000: 'Fog',
        2100: 'Light Fog',
        4000: 'Drizzle',
        4001: 'Rain',
        4200: 'Light Rain',
        4201: 'Heavy Rain',
        5000: 'Snow',
        5001: 'Flurries',
        5100: 'Light Snow',
        5101: 'Heavy Snow',
        6000: 'Freezing Drizzle',
        6001: 'Freezing Rain',
        6200: 'Light Freezing Rain',
        6201: 'Heavy Freezing Rain',
        7000: 'Ice Pellets',
        7101: 'Heavy Ice Pellets',
        7102: 'Light Ice Pellets',
        8000: 'Thunderstorm',
    }.get(code, 'Unknown')

async def chat(weather_agent: Agent, deps: Deps):
    """Interactive chat loop for weather queries."""
    print("Weather Chat Agent (type 'exit' to quit)")

    messages: List[ModelMessage] = []
    
    while True:
        try:
            # Get user input
            user_query = input("You: ").strip()
            
            # Exit condition
            if user_query.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            # Skip empty queries
            if not user_query:
                continue
            
            # Run the weather agent with the query
            result = await weather_agent.run(user_query, deps=deps, message_history=messages)

            messages = result.all_messages()
            
            # Print the agent's response
            print("Agent:", result.data)
        
        except Exception as e:
            print(f"An error occurred: {e}")

async def main():
    async with AsyncClient() as client:
        # create a free API key at https://www.tomorrow.io/weather-api/
        weather_api_key = os.getenv('WEATHER_API_KEY')
        # create a free API key at https://geocode.maps.co/
        geo_api_key = os.getenv('GEO_API_KEY')
        deps = Deps(
            client=client, weather_api_key=weather_api_key, geo_api_key=geo_api_key
        )

        # Start the chat loop
        await chat(weather_agent, deps)


if __name__ == '__main__':
    asyncio.run(main())