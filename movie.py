"""Movie API to allocate movie cradentials"""
import os
import requests
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

# pylint: disable=invalid-name
def trendingMoviesOfTheYear(year):
    """Function quarying data from wiki based on title"""
    url = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "include_adult": "false",
        "include_video": "true",
        "language": "en-US",
        "page": "1",
        "sort_by": "popularity.desc",
        "year": "2023",
    }
    headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {os.getenv('Movie_Authorization_Token')}"
    }
    data = requests.get(url, headers=headers, params=params).json()
    return data
