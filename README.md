
# Amenity Finder App

## Overview

The **Amenity Finder App** helps users explore amenities (e.g., hospitals, schools, pharmacies) around a specific location. It provides interactive maps, calculates the shortest routes to amenities, and shows detailed results in an easy-to-use interface.

## Features

- **Interactive Map**: View selected location with nearby amenities and routes.
- **Amenity Search**: Search for amenities within a customizable radius.
- **Custom Markers**: Different amenity types have distinct colored markers.
- **Results Tab**: View detailed information about the nearest amenities.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/konishon/lalpurja-map.git
   cd amenity-finder-app
   ```

2. Create a virtual environment (optional):
   ```bash
   python -m venv venv
   source venv/bin/activate  # For Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Usage

1. **Select Location**: Use predefined locations or enter coordinates manually.
2. **Choose Amenities**: Select the types of amenities to search for.
3. **Adjust Radius**: Set the search radius using the slider.
4. **View Map & Results**: Check the map with amenities and routes in the **Map** tab, and see detailed results in the **Results** tab.

## License

This project is licensed under the MIT License.