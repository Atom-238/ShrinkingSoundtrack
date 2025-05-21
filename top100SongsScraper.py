import urllib.request
from html.parser import HTMLParser
import csv


class BillboardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell_data = ''
        self.current_row_data = []
        self.songs = []
        self.in_target_table = False
        self.header_found = False
        self.current_headers = []
        self.artist_buffer = None  # To track rowspan artists
        self.artist_rowspan = 0    # How many rows left to apply artist buffer

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and 'class' in attrs and 'wikitable' in attrs['class']:
            self.in_table = True
            self.header_found = False
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row_data = []
        elif tag == 'td' and self.in_row and self.in_target_table:
            self.in_cell = True
            self.current_cell_data = ''
            self.current_td_attrs = attrs  # Save attributes like rowspan
        elif tag == 'th' and self.in_row and self.in_table:
            self.in_cell = True
            self.current_cell_data = ''

    def handle_endtag(self, tag):
        if tag == 'table' and self.in_table:
            self.in_table = False
            self.in_target_table = False
        elif tag == 'tr' and self.in_row:
            if self.in_table and not self.header_found and self.current_headers:
                if self.current_headers[:3] == ['No.', 'Title', 'Artist(s)']:
                    self.in_target_table = True
                self.header_found = True
            if self.in_target_table and len(self.current_row_data) >= 2:
                # Handle artist rowspan buffer
                if len(self.current_row_data) == 3:
                    artist = self.current_row_data[2].strip()
                    if 'rowspan' in self.current_td_attrs:
                        try:
                            self.artist_rowspan = int(
                                self.current_td_attrs['rowspan']) - 1
                            self.artist_buffer = artist
                        except:
                            pass
                elif len(self.current_row_data) == 2:
                    if self.artist_buffer and self.artist_rowspan > 0:
                        artist = self.artist_buffer
                        self.artist_rowspan -= 1
                    else:
                        artist = ''
                else:
                    artist = ''

                title = self.current_row_data[1].strip()
                title = title.strip('"').strip('“”').strip('“').strip('”')
                combined = f'{title} - {artist}'.strip(' - ')
                self.songs.append(combined)
            self.in_row = False
        elif tag in ('td', 'th') and self.in_cell:
            if self.in_table and self.in_row:
                if not self.header_found and tag == 'th':
                    self.current_headers.append(self.current_cell_data.strip())
                elif self.in_target_table and tag == 'td':
                    self.current_row_data.append(
                        self.current_cell_data.strip())
            self.in_cell = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell_data += data


def fetch_html(url):
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8')


def save_combined_csv(all_songs_by_year):
    filename = 'billboard_top_100_combined_title_artist.csv'
    years = sorted(all_songs_by_year.keys())
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(years)
        for i in range(100):
            row = []
            for year in years:
                if i < len(all_songs_by_year[year]):
                    row.append(all_songs_by_year[year][i])
                else:
                    row.append('')
            writer.writerow(row)


def main():
    all_songs_by_year = {}
    for year in range(2000, 2025):
        print(f'Fetching year {year}...')
        url = f'https://en.wikipedia.org/wiki/Billboard_Year-End_Hot_100_singles_of_{
            year}'
        try:
            html_content = fetch_html(url)
        except Exception as e:
            print(f'Error fetching {year}: {e}')
            continue

        parser = BillboardParser()
        parser.feed(html_content)

        if not parser.songs:
            print(f'No songs found for {year}!')
        else:
            all_songs_by_year[year] = parser.songs[:100]
            print(f'Found {len(parser.songs[:100])} songs for {year}.')

    if all_songs_by_year:
        save_combined_csv(all_songs_by_year)
        print('Combined CSV file with titles and artists saved!')


if __name__ == '__main__':
    main()
