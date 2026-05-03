# nova-binge

Media companion for Hermes — search, download and manage movies & series via Radarr, Sonarr, qBittorrent and Prowlarr.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Hermes                               │
│                   (natural language)                     │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                    nova-binge                             │
│  • Search (Prowlarr)                                     │
│  • Add to library (Radarr/Sonarr)                        │
│  • Monitor downloads (qBittorrent)                       │
│  • TTS notifications                                    │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│              Windows Host (v1)                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │Radarr   │ │Sonarr   │ │Prowlarr │ │qBittorrent  │    │
│  │:7878    │ │:8989    │ │:9696    │ │:8080        │    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Quick Start (Phase 1: Windows Host)

Configure your Windows apps in `config.yaml`:

```yaml
# Windows host configuration
windows_host: "172.20.16.1"

radarr:
  url: "http://172.20.16.1:7878"
  api_key: "your_radarr_api_key"

sonarr:
  url: "http://172.20.16.1:8989"
  api_key: "your_sonarr_api_key"

prowlarr:
  url: "http://172.20.16.1:9696"
  api_key: "your_prowlarr_api_key"

qbittorrent:
  url: "http://172.20.16.1:8080"
  username: "admin"
  password: "your_password"
```

## Usage Examples

```bash
# Search for a movie
python nova_binge.py search movie "Dune Part Two"

# Search for a TV series  
python nova_binge.py search series "Severance"

# Add movie to Radarr
python nova_binge.py add movie "Dune Part Two"

# Add series to Sonarr
python nova_binge.py add series "Severance" --season 1

# Check download status
python nova_binge.py downloads

# List library
python nova_binge.py library radarr
python nova_binge.py library sonarr
```

## Phase 2: Docker Compose (Future)

Run services in WSL via Docker:

```bash
docker-compose up -d
# Radarr: :7878
# Sonarr: :8989  
# Prowlarr: :9696
# qBittorrent: :8080
```

## API Integration

### Radarr API
- `GET /api/v3/movie` — List movies
- `POST /api/v3/movie` — Add movie
- `DELETE /api/v3/movie/{id}` — Delete movie

### Sonarr API
- `GET /api/v3/series` — List series
- `POST /api/v3/series` — Add series
- `GET /api/v3/episode?seriesId={id}` — Get episodes

### Prowlarr API
- `GET /api/v1/indexerproxy` — Search indexers
- `POST /api/v1/indexerproxy` — Add indexer

### qBittorrent API
- `GET /api/v2/app/log` — App logs
- `GET /api/v2/torrents/info` — Torrent list
- `POST /api/v2/torrents/add` — Add torrent

## License

MIT