"""Analizza i brani finiti in 'Altri Generi' per capire quali tag MusicBrainz
non sono coperti dalle GENRE_RULES. Nessuna chiamata di rete: legge solo la cache.

Uso:
    python3 backend/analyze_genres.py
"""

import json
from collections import Counter
from pathlib import Path

CATALOG = Path.home() / ".drops" / "spotify-library.json"


def main() -> None:
    if not CATALOG.exists():
        raise SystemExit(f"Catalogo non trovato: {CATALOG}")
    tracks = json.loads(CATALOG.read_text()).get("tracks", [])

    altri = [t for t in tracks if t.get("genre_folder") == "Altri Generi"]
    con_tag = [t for t in altri if t.get("genres")]
    senza_tag = [t for t in altri if not t.get("genres")]

    print(f"Totale brani: {len(tracks)}")
    print(f"In 'Altri Generi': {len(altri)}")
    print(f"  - con tag MusicBrainz (recuperabili con nuove regole): {len(con_tag)}")
    print(f"  - senza alcun tag (artista non trovato/senza tag): {len(senza_tag)}")

    tag_counts = Counter(
        tag.lower() for t in con_tag for tag in t.get("genres", [])
    )
    print("\nTag piu' frequenti tra gli 'Altri Generi' (i candidati per nuove regole):\n")
    for tag, n in tag_counts.most_common(45):
        print(f"  {n:4}  {tag}")


if __name__ == "__main__":
    main()
