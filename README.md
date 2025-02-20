# Freesound Downloader

A Python script to download your bookmarked sounds from Freesound.org, organizing them by category and maintaining licensing information.

## Features

- Download all bookmarked sounds from Freesound.org
- Organize downloads by bookmark categories
- Track and maintain licensing information
- Skip existing downloads while updating metadata
- Command line interface with config file support

## Setup

1. Install Python 3.7 or higher
2. Install Poetry (dependency management)
3. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/freesound-downloader.git
   cd freesound-downloader
   ```
4. Install dependencies:
   ```bash
   poetry install
   ```

## Configuration

Create a `config.ini` file with your Freesound credentials:

```ini
[credentials]
username = your_username
password = your_password
```

## Usage

Run the script using one of these methods:

```bash
# Using config file (recommended)
poetry run python freesound-downloader.py -c config.ini -o output

# Using command line arguments
poetry run python freesound-downloader.py -u username -p password -o output

# Interactive mode
poetry run python freesound-downloader.py
```

## Output Structure

```
output/
├── category1/
│   ├── sound1.wav
│   ├── sound2.wav
│   └── licensing.json
├── category2/
│   ├── sound3.wav
│   └── licensing.json
```

The `licensing.json` file contains metadata for each sound:

```json
[
  {
    "title": "Sound Title",
    "author": "Author Name",
    "url": "https://freesound.org/people/author/sounds/123/",
    "description": "Sound description",
    "license": {
      "name": "Attribution 4.0",
      "url": "https://creativecommons.org/licenses/by/4.0/"
    },
    "filename": "sound.wav"
  }
]
```

## Dependencies

- requests
- beautifulsoup4
- configparser

## License

MIT License
