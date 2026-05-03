#!/usr/bin/env python3
"""
nova-binge — Media companion for Hermes
Search, download and manage movies & series via Radarr, Sonarr, qBittorrent, Prowlarr
"""

import argparse
import sys
import os
import yaml
import requests
from pathlib import Path


class NovaBinge:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or Path(__file__).parent / "config.yaml"
        self.config = self._load_config()
        
        self.radarr_url = self.config["radarr"]["url"]
        self.radarr_api = self.config["radarr"]["api_key"]
        
        self.sonarr_url = self.config["sonarr"]["url"]
        self.sonarr_api = self.config["sonarr"]["api_key"]
        
        self.prowlarr_url = self.config["prowlarr"]["url"]
        self.prowlarr_api = self.config["prowlarr"]["api_key"]
        
        self.qbit_url = self.config["qbittorrent"]["url"]
        self.qbit_user = self.config["qbittorrent"]["username"]
        self.qbit_pass = self.config["qbittorrent"]["password"]
        
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": self.radarr_api})
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if not Path(self.config_path).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    # === RADARR ===
    
    def get_movies(self) -> list:
        """Get all movies in Radarr library"""
        resp = self.session.get(f"{self.radarr_url}/api/v3/movie")
        resp.raise_for_status()
        return resp.json()
    
    def search_movie(self, query: str) -> list:
        """Search for a movie via Radarr"""
        resp = self.session.get(
            f"{self.radarr_url}/api/v3/movie/lookup",
            params={"term": query}
        )
        resp.raise_for_status()
        return resp.json()
    
    def add_movie(self, query: str, quality_profile_id: int = 1, 
                  root_folder_path: str = None) -> dict:
        """Add a movie to Radarr library"""
        # First search for the movie
        results = self.search_movie(query)
        if not results:
            raise ValueError(f"No movie found for query: {query}")
        
        movie = results[0]
        
        # Get root folder if not provided
        if not root_folder_path:
            folders = self.session.get(f"{self.radarr_url}/api/v3/rootfolder")
            root_folder_path = folders.json()[0]["path"]
        
        # Add movie payload
        payload = {
            "title": movie["title"],
            "titles": movie.get("titles", []),
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder_path,
            "tmdbId": movie["tmdbId"],
            "year": movie.get("year"),
            "addOptions": {
                "searchForMovie": True
            }
        }
        
        resp = self.session.post(
            f"{self.radarr_url}/api/v3/movie",
            json=payload
        )
        resp.raise_for_status()
        return resp.json()
    
    # === SONARR ===
    
    def get_series(self) -> list:
        """Get all series in Sonarr library"""
        self.session.headers["X-Api-Key"] = self.sonarr_api
        resp = self.session.get(f"{self.sonarr_url}/api/v3/series")
        resp.raise_for_status()
        return resp.json()
    
    def search_series(self, query: str) -> list:
        """Search for a TV series via Sonarr"""
        self.session.headers["X-Api-Key"] = self.sonarr_api
        resp = self.session.get(
            f"{self.sonarr_url}/api/v3/series/lookup",
            params={"term": query}
        )
        resp.raise_for_status()
        return resp.json()
    
    def add_series(self, query: str, quality_profile_id: int = 1,
                   season_folder: bool = True, search_for_series: bool = True) -> dict:
        """Add a series to Sonarr library"""
        self.session.headers["X-Api-Key"] = self.sonarr_api
        
        # Search for series
        results = self.search_series(query)
        if not results:
            raise ValueError(f"No series found for query: {query}")
        
        series = results[0]
        
        # Get root folders
        folders = self.session.get(f"{self.sonarr_url}/api/v3/rootfolder")
        root_folder_path = folders.json()[0]["path"]
        
        # Get profile IDs
        profiles = self.session.get(f"{self.sonarr_url}/api/v3/qualityprofile")
        quality_profile_id = profiles.json()[0]["id"]
        
        payload = {
            "title": series["title"],
            "titles": series.get("titles", []),
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder_path,
            "tvdbId": series["tvdbId"],
            "seasonFolder": season_folder,
            "addOptions": {
                "searchForSeason": search_for_series,
                "searchForEpisodes": search_for_series
            }
        }
        
        resp = self.session.post(
            f"{self.sonarr_url}/api/v3/series",
            json=payload
        )
        resp.raise_for_status()
        return resp.json()
    
    def get_series_episodes(self, series_id: int) -> list:
        """Get all episodes for a series"""
        self.session.headers["X-Api-Key"] = self.sonarr_api
        resp = self.session.get(
            f"{self.sonarr_url}/api/v3/episode",
            params={"seriesId": series_id}
        )
        resp.raise_for_status()
        return resp.json()
    
    # === PROWLARR ===
    
    def search_indexers(self, query: str) -> list:
        """Search all indexers via Prowlarr"""
        # Prowlarr uses same auth as Radarr
        self.session.headers["X-Api-Key"] = self.prowlarr_api
        resp = self.session.get(
            f"{self.prowlarr_url}/api/v1/indexerproxy",
            params={"t": "search", "q": query}
        )
        resp.raise_for_status() if resp.status_code != 204 else None
        return resp.json() if resp.content else []
    
    def get_indexers(self) -> list:
        """Get configured indexers"""
        self.session.headers["X-Api-Key"] = self.prowlarr_api
        resp = self.session.get(f"{self.prowlarr_url}/api/v1/indexer")
        resp.raise_for_status()
        return resp.json()
    
    # === QBITTORRENT ===
    
    def _qbit_auth(self) -> str:
        """Get qBittorrent session cookie"""
        # Step 1: Login and get session cookie
        login_resp = self.session.post(
            f"{self.qbit_url}/api/v2/auth/login",
            data={"username": self.qbit_user, "password": self.qbit_pass}
        )
        
        # Extract SID from Set-Cookie header
        cookie_header = login_resp.headers.get("Set-Cookie", "")
        if "SID=" in cookie_header:
            sid = login_resp.cookies.get("SID")
            return sid
        return None
    
    def get_torrents(self) -> list:
        """Get all torrents in qBittorrent"""
        # qBittorrent requires login first to get session
        login_resp = self.session.post(
            f"{self.qbit_url}/api/v2/auth/login",
            data={"username": self.qbit_user, "password": self.qbit_pass}
        )
        
        # Check login success - response should be "Ok."
        if login_resp.text != "Ok.":
            raise Exception(f"qBittorrent login failed: {login_resp.text}")
        
        # Now get torrents with the session cookie
        resp = self.session.get(f"{self.qbit_url}/api/v2/torrents/info")
        resp.raise_for_status()
        return resp.json()
    
    def get_torrent_files(self, hash: str) -> list:
        """Get files for a specific torrent"""
        resp = self.session.get(
            f"{self.qbit_url}/api/v2/torrents/files",
            params={"hash": hash}
        )
        resp.raise_for_status()
        return resp.json()
    
    def pause_torrent(self, hash: str) -> bool:
        """Pause a torrent"""
        resp = self.session.post(
            f"{self.qbit_url}/api/v2/torrents/pause",
            data={"hashes": hash}
        )
        return resp.status_code == 200
    
    def resume_torrent(self, hash: str) -> bool:
        """Resume a torrent"""
        resp = self.session.post(
            f"{self.qbit_url}/api/v2/torrents/resume",
            data={"hashes": hash}
        )
        return resp.status_code == 200
    
    # === HELPERS ===
    
    def check_services(self) -> dict:
        """Check if all services are reachable"""
        status = {}
        
        # Radarr
        try:
            self.session.headers["X-Api-Key"] = self.radarr_api
            r = self.session.get(f"{self.radarr_url}/api/v3/system/status")
            status["radarr"] = "OK" if r.status_code == 200 else f"Error {r.status_code}"
        except Exception as e:
            status["radarr"] = f"Failed: {e}"
        
        # Sonarr
        try:
            self.session.headers["X-Api-Key"] = self.sonarr_api
            r = self.session.get(f"{self.sonarr_url}/api/v3/system/status")
            status["sonarr"] = "OK" if r.status_code == 200 else f"Error {r.status_code}"
        except Exception as e:
            status["sonarr"] = f"Failed: {e}"
        
        # qBittorrent
        try:
            # qBittorrent requires form-based login
            login_resp = self.session.post(
                f"{self.qbit_url}/api/v2/auth/login",
                data={"username": self.qbit_user, "password": self.qbit_pass}
            )
            if login_resp.text == "Ok.":
                r = self.session.get(f"{self.qbit_url}/api/v2/app/version")
                status["qbittorrent"] = "OK" if r.status_code == 200 else f"Error {r.status_code}"
            else:
                status["qbittorrent"] = "Login failed"
        except Exception as e:
            status["qbittorrent"] = f"Failed: {e}"
        
        return status


def main():
    parser = argparse.ArgumentParser(description="nova-binge — media companion")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Check services
    subparsers.add_parser("status", help="Check service status")
    
    # Search commands
    search_parser = subparsers.add_parser("search", help="Search media")
    search_parser.add_argument("type", choices=["movie", "series"], help="Media type")
    search_parser.add_argument("query", help="Search query")
    
    # Add commands
    add_parser = subparsers.add_parser("add", help="Add media to library")
    add_parser.add_argument("type", choices=["movie", "series"], help="Media type")
    add_parser.add_argument("query", help="Media name")
    add_parser.add_argument("--season", type=int, help="Specific season (series only)")
    
    # Library commands
    lib_parser = subparsers.add_parser("library", help="Show library")
    lib_parser.add_argument("type", choices=["radarr", "sonarr"], help="Which library")
    
    # Downloads
    subparsers.add_parser("downloads", help="Show active downloads")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    nb = NovaBinge()
    
    if args.command == "status":
        status = nb.check_services()
        print("=== Service Status ===")
        for service, state in status.items():
            print(f"  {service}: {state}")
    
    elif args.command == "search":
        if args.type == "movie":
            results = nb.search_movie(args.query)
            print(f"=== Search Results: {args.query} ===")
            for i, m in enumerate(results[:10], 1):
                year = m.get("year", "N/A")
                print(f"  {i}. {m['title']} ({year}) - TMDB: {m.get('tmdbId')}")
        else:
            results = nb.search_series(args.query)
            print(f"=== Search Results: {args.query} ===")
            for i, s in enumerate(results[:10], 1):
                year = s.get("year", "N/A")
                print(f"  {i}. {s['title']} ({year}) - TVDB: {s.get('tvdbId')}")
    
    elif args.command == "add":
        if args.type == "movie":
            result = nb.add_movie(args.query)
            print(f"Added: {result.get('title')}")
        else:
            result = nb.add_series(args.query)
            print(f"Added: {result.get('title')}")
    
    elif args.command == "library":
        if args.type == "radarr":
            movies = nb.get_movies()
            print("=== Radarr Library ===")
            for m in movies:
                status = m.get("status", "N/A")
                print(f"  {m['title']} ({m.get('year')}) - {status}")
        else:
            series = nb.get_series()
            print("=== Sonarr Library ===")
            for s in series:
                status = s.get("status", "N/A")
                print(f"  {s['title']} - {status}")
    
    elif args.command == "downloads":
        torrents = nb.get_torrents()
        print("=== Active Downloads ===")
        for t in torrents:
            progress = t.get("progress", 0)
            name = t.get("name", "Unknown")
            print(f"  {name} - {progress:.1f}%")


if __name__ == "__main__":
    main()