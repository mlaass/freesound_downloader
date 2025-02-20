import requests
from bs4 import BeautifulSoup
import os
import json
from urllib.parse import urljoin
import re
import argparse
import configparser


class FreesoundDownloader:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.base_url = "https://freesound.org"
        self.username = username
        self.password = password
        self.csrf_token = None

    def login(self):
        """Login to Freesound and get authentication cookies"""
        # First get the login page to extract CSRF token
        login_page = self.session.get(f"{self.base_url}/home/login/")
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

        # Perform login
        login_data = {
            "username": self.username,
            "password": self.password,
            "csrfmiddlewaretoken": csrf_token,
            "next": "/home/bookmarks/",
        }

        response = self.session.post(
            f"{self.base_url}/home/login/", data=login_data, headers={"Referer": f"{self.base_url}/home/login/"}
        )

        return response.ok

    def get_bookmark_categories(self):
        """Get all bookmark categories and their URLs"""
        print(f"Getting bookmark categories")
        bookmarks_page = self.session.get(f"{self.base_url}/home/bookmarks/")
        soup = BeautifulSoup(bookmarks_page.text, "html.parser")

        categories = {}
        category_list = soup.find_all("li", {"class": None})  # Bookmark categories don't have a class

        for category in category_list:
            link = category.find("a")
            if link and "bookmarks" in link.get("href", ""):
                name = link.text.strip()
                url = urljoin(self.base_url, link["href"])
                categories[name] = url
        print(f"Found {len(categories)} bookmark categories: {categories.keys()}")
        return categories

    def get_sounds_from_category(self, category_url):
        """Get all sounds from a category page"""
        page = self.session.get(category_url)
        soup = BeautifulSoup(page.text, "html.parser")

        sounds = []
        # Find sound entries using the bw-player div class
        sound_entries = soup.find_all("div", {"class": "bw-player"})

        for entry in sound_entries:
            try:
                # Extract data from the data attributes
                sound_id = entry["data-sound-id"]
                # Find the parent container and then find the author link
                container = entry.find_parent("div", {"class": "col-6"})
                author_link = container.find("div", {"class": "ellipsis"}).find("a")
                author = author_link.text.strip()

                sound_info = {
                    "title": entry["data-title"],
                    "url": f"{self.base_url}/people/{author}/sounds/{sound_id}/",  # Full URL to sound page
                    "duration": float(entry["data-duration"]),
                    "mp3_url": entry["data-mp3"],
                    "ogg_url": entry["data-ogg"],
                }
                print(f"Found sound: {sound_info['title']} by {author} at {sound_info['url']}")
                sounds.append(sound_info)
            except Exception as e:
                print(f"Error parsing sound entry: {str(e)}")
                print(f"Entry HTML: {entry}")

        return sounds

    def download_sound(self, sound_url, output_dir):
        """Download a sound and its metadata"""
        try:
            print(f"\nFetching sound page: {sound_url}")
            sound_page = self.session.get(sound_url)
            if not sound_page.ok:
                print(f"Failed to fetch page: Status {sound_page.status_code}")
                return None

            soup = BeautifulSoup(sound_page.text, "html.parser")

            # Debug: Save HTML for inspection
            with open("debug_page.html", "w") as f:
                f.write(sound_page.text)

            # Find the information section
            info_section = soup.find("div", {"class": "bw-sound-page__information"})
            if not info_section:
                print("Could not find information section")
                return None

            # Extract sound information from the page
            title_elem = info_section.find("h1")
            if not title_elem:
                print("Could not find title element")
                return None
            title = title_elem.find("a").text.strip()

            user_section = info_section.find("div", {"class": "bw-sound-page__user"})
            if not user_section:
                print("Could not find user section")
                return None
            author = user_section.find("a").text.strip()

            desc_section = info_section.find("div", {"id": "soundDescriptionSection"})
            if not desc_section:
                print("Could not find description section")
                return None
            description = desc_section.text.strip()

            # Find license info (in the sidebar)
            sidebar = soup.find("div", {"class": "bw-sound__sidebar"})
            if not sidebar:
                print("Could not find sidebar")
                return None

            license_link = sidebar.find("a", {"title": "Go to the full license text"})
            if not license_link:
                print("Could not find license link")
                return None

            license_text = license_link.text.strip()
            license_url = license_link["href"]

            # Find download button URL
            download_button = soup.find("a", {"class": "sound-download-button"})
            if not download_button:
                print("Could not find download button")
                return None
            download_url = download_button["href"]

            print(f"Found metadata: {title} by {author}")
            print(f"Download URL: {download_url}")

            # Prepare metadata
            metadata = {
                "title": title,
                "author": author,
                "url": sound_url,
                "description": description,
                "license": {"name": license_text, "url": license_url},
            }

            # Check if file already exists
            expected_filename = download_url.split("/")[-1]  # Get filename from download URL
            file_path = os.path.join(output_dir, expected_filename)

            if os.path.exists(file_path):
                print(f"File already exists: {file_path}")
                metadata["filename"] = expected_filename
                return metadata

            # Download the sound file if it doesn't exist
            print(f"Found metadata: {title} by {author}")
            print(f"Download URL: {download_url}")

            download_response = self.session.get(urljoin(self.base_url, download_url))
            if download_response.ok:
                # Get filename from Content-Disposition or create one from title
                filename = re.findall("filename=(.+)", download_response.headers.get("content-disposition", ""))
                if filename:
                    filename = filename[0].strip('"')
                else:
                    filename = f"{title.replace(' ', '_')}.wav"

                file_path = os.path.join(output_dir, filename)
                print(f"Saving to: {file_path}")

                with open(file_path, "wb") as f:
                    f.write(download_response.content)

                metadata["filename"] = expected_filename
                print(f"Saved to: {file_path}")
                return metadata
            else:
                print(f"Download failed: Status {download_response.status_code}")

        except Exception as e:
            print(f"Error downloading {sound_url}: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

        return None

    def load_existing_metadata(self, category_dir):
        """Load existing metadata from licensing.json if it exists"""
        licensing_file = os.path.join(category_dir, "licensing.json")
        if os.path.exists(licensing_file):
            with open(licensing_file, "r") as f:
                return json.load(f)
        return []

    def download_category(self, category_name, category_url, base_output_dir):
        """Download all sounds from a category"""
        # Create category directory
        category_dir = os.path.join(base_output_dir, category_name)
        os.makedirs(category_dir, exist_ok=True)

        # Load existing metadata
        existing_metadata = self.load_existing_metadata(category_dir)
        existing_urls = {item["url"] for item in existing_metadata}

        # Get all sounds in category
        sounds = self.get_sounds_from_category(category_url)
        print(f"Found {len(sounds)} sounds in category '{category_name}'")

        # Download each sound and collect metadata
        metadata_list = []  # Start fresh to update all metadata
        for i, sound in enumerate(sounds, 1):
            print(f"Processing {i}/{len(sounds)}: {sound['title']}")
            metadata = self.download_sound(sound["url"], category_dir)
            if metadata:
                metadata_list.append(metadata)
                # Update licensing file after each successful download/update
                with open(os.path.join(category_dir, "licensing.json"), "w") as f:
                    json.dump(metadata_list, f, indent=2)
            else:
                print(f"Failed to process {sound['title']}")
                # Keep old metadata if we failed to get new metadata
                old_metadata = next((item for item in existing_metadata if item["url"] == sound["url"]), None)
                if old_metadata:
                    metadata_list.append(old_metadata)


def load_config(config_path):
    """Load configuration from file"""
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
        if "credentials" in config:
            return {
                "username": config["credentials"].get("username").strip(),
                "password": config["credentials"].get("password").strip(),
            }
    return None


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Download sounds from Freesound bookmarks")
    parser.add_argument("--output", "-o", help="Output directory path")
    parser.add_argument("--config", "-c", help="Path to config file", default="config.ini")
    parser.add_argument("--username", "-u", help="Freesound username")
    parser.add_argument("--password", "-p", help="Freesound password")

    args = parser.parse_args()

    # Try to load credentials from config file if not provided in command line
    config = None
    if not (args.username and args.password):
        config = load_config(args.config)

    # Get credentials (priority: command line > config file > user input)
    username = args.username or (config["username"] if config else None) or input("Enter your Freesound username: ")
    password = args.password or (config["password"] if config else None) or input("Enter your Freesound password: ")

    # Get output directory (priority: command line > user input)
    output_dir = args.output or input("Enter output directory path: ")

    # Create downloader instance
    downloader = FreesoundDownloader(username, password)
    print(f"Downloader instance created")
    # Login
    if not downloader.login():
        print("Login failed!")
        return

    # Get categories
    categories = downloader.get_bookmark_categories()

    # Download each category
    for category_name, category_url in categories.items():
        print(f"Downloading category: {category_name}")
        downloader.download_category(category_name, category_url, output_dir)
        print(f"Finished downloading category: {category_name}")


if __name__ == "__main__":
    main()
