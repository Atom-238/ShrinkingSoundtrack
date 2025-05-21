import csv
import random
import re
import time
import requests


CLIENT_ID = 'KEY'
CLIENT_SECRET = 'KEY'


def get_spotify_token(client_id, client_secret):
    url = 'https://accounts.spotify.com/api/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials'}
    response = requests.post(url, headers=headers,
                             data=data, auth=(client_id, client_secret))
    if response.status_code != 200:
        raise Exception(f"Failed to get token: {response.text}")
    return response.json()['access_token']


def get_song_duration(song, artist, token):
    song_clean = re.sub(r'\s+\(?feat(?:uring)?\..*', '',
                        song, flags=re.IGNORECASE).strip()
    search_attempts = [
        f"track:{song_clean} artist:{artist}",
        f"{song_clean} {artist}",
        f"{song_clean}",
    ]

    search_url = 'https://api.spotify.com/v1/search'
    headers = {'Authorization': f'Bearer {token}'}

    for idx, attempt in enumerate(search_attempts, start=1):
        try:
            print(f"🔍 Attempt {idx}/3: Searching '{attempt}'...")
            params = {'q': attempt, 'type': 'track', 'limit': 1}
            response = requests.get(
                search_url, headers=headers, params=params, timeout=10)

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                print(f"⏳ Rate limited. Sleeping {retry_after}s...")
                time.sleep(retry_after)
                continue

            if response.status_code != 200:
                print(f"⚠️ API error {response.status_code} for {
                      song} by {artist}")
                return None

            items = response.json().get('tracks', {}).get('items', [])
            if items:
                duration_seconds = items[0]['duration_ms'] / 1000
                print(f"✅ Found: '{song}' by {
                      artist} → {duration_seconds} sec")
                return round(duration_seconds, 2)

        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout searching '{attempt}'. Skipping.")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    print(f"❌ Not found after all attempts: {song} by {artist}")
    return None


def main():
    input_csv = 'Billboard-Top-100-Combined-2000-2024.csv'
    output_csv = 'randomly-selected-songs-with-durations.csv'
    songs_by_year = {}

    # Load CSV data
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            for year, song in zip(headers, row):
                songs_by_year.setdefault(year, []).append(song)

    token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
    final_data_by_year = {}

    # Process songs year by year (no threads)
    for year_idx, (year, songs) in enumerate(sorted(songs_by_year.items()), start=1):
        print(f"\n=== Processing year {
              year} ({year_idx}/{len(songs_by_year)}) ===")
        selected_songs = random.sample(songs, min(20, len(songs)))
        year_results = []

        for song_idx, entry in enumerate(selected_songs, start=1):
            print(f"\n→ [{year} | Song {song_idx}/20]: {entry}")
            if ' - ' not in entry:
                print(f"⚠️ Skipping malformed entry: {entry}")
                continue

            song, artist = entry.split(' - ', 1)
            duration = get_song_duration(song, artist, token)
            song_artist_str = f"{song} - {artist}"
            year_results.append(
                (song_artist_str, duration if duration else 'N/A'))

        final_data_by_year[year] = year_results

    # Write output as wide CSV
    all_rows = []
    for i in range(20):  # Assume 20 rows per year
        row = []
        for year in sorted(final_data_by_year.keys()):
            if i < len(final_data_by_year[year]):
                song, duration = final_data_by_year[year][i]
                row.extend([song, duration])
            else:
                row.extend(['', ''])
        all_rows.append(row)

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = []
        for year in sorted(final_data_by_year.keys()):
            header.extend([f"{year} Songs", f"{year} Durations"])
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"\n✅ All done! Output saved to {output_csv}")


if __name__ == '__main__':
    main()
