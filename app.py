import streamlit as st
import osmnx as ox
import geopandas as gpd
import pandas as pd
import networkx as nx
from shapely.geometry import Point, Polygon
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(layout="wide", page_title="Amenity Finder")

st.title("Amenity Finder")

if 'latitude_input' not in st.session_state:
    st.session_state['latitude_input'] = 27.7172
if 'longitude_input' not in st.session_state:
    st.session_state['longitude_input'] = 85.3240

property_list_url = "https://backend.lalpurjanepal.com.np/properties/all-properties/"
property_detail_url_template = "https://backend.lalpurjanepal.com.np/properties/properties/{}"

@st.cache_data
def fetch_property_list():
    response = requests.get(property_list_url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error fetching property list.")
        return []

@st.cache_data
def fetch_property_details(property_id):
    response = requests.get(property_detail_url_template.format(property_id))
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching property details for ID {property_id}.")
        return {}

st.sidebar.header("🔍 Select a Property")
properties = fetch_property_list()

if properties:
    property_options = {prop['title']: {'id': prop['id'], 'slug': prop['slug']} for prop in properties}
    selected_property = st.sidebar.selectbox("🏠 Select Property", options=list(property_options.keys()))
    selected_property_data = property_options[selected_property]
    selected_property_id = selected_property_data['id']
    selected_property_slug = selected_property_data['slug']

    property_details = fetch_property_details(selected_property_id)    
    selected_property_thumbnail = property_details.get('thumbnail', None)
    if selected_property_thumbnail:
        st.sidebar.image(selected_property_thumbnail, caption="Property Thumbnail", use_column_width=True)

    if property_details and "location_value" in property_details:
        location_value = property_details["location_value"]
        latitude, longitude = map(float, location_value.split(","))
    else:
        latitude, longitude = 27.7172, 85.3240  # Default to Kathmandu if no valid location

    property_url = f"https://lalpurjanepal.com.np/properties/{selected_property_slug}-{selected_property_id}"
    
    st.sidebar.markdown(f"🔗 [View on Lalpurja]({property_url})")
else:
    st.error("No properties available.")
    latitude, longitude = 27.7172, 85.3240  # Default location if no properties


st.sidebar.markdown("---")
st.sidebar.header("📍 Search Radius")
radius = st.sidebar.slider("Adjust Radius (meters)", min_value=500, max_value=5000, value=500, step=100, key="radius_slider")


class OSMHandler:
    def __init__(self, point, radius):
        self.point = point
        self.radius = radius
        self.graph = self.fetch_graph()  

    def fetch_graph(self):
        return ox.graph_from_point(self.point, dist=self.radius, network_type='walk')

    def fetch_amenities(self, selected_amenities):
        tags = {'amenity': selected_amenities}
        gdf_amenities = ox.features_from_point(self.point, tags=tags, dist=self.radius)
        return gdf_amenities

    def calculate_route(self, orig_node, dest_point):
        if isinstance(dest_point, Polygon):
            dest_point = dest_point.centroid
        dest_node = ox.distance.nearest_nodes(self.graph, X=dest_point.x, Y=dest_point.y)
        try:
            route = nx.shortest_path(self.graph, orig_node, dest_node, weight='length')
            route_coords = [(self.graph.nodes[node]['y'], self.graph.nodes[node]['x']) for node in route]
            route_length = nx.shortest_path_length(self.graph, orig_node, dest_node, weight='length')
        except nx.NetworkXNoPath:
            route_coords = []  # If no route is found, return an empty list
            route_length = float('inf')
        return route_coords, route_length

    def get_nearest_node(self, lat, lon):
        return ox.distance.nearest_nodes(self.graph, X=lon, Y=lat)


@st.cache_data
def fetch_graph_and_amenities(lat, lon, radius, selected_amenities):
    osm_handler = OSMHandler((lat, lon), radius)
    graph = osm_handler.graph
    amenities = osm_handler.fetch_amenities(selected_amenities)
    return graph, amenities


def generate_facility_insights_and_add_routes(m, point, gdf, graph, orig_node, radius):
    facility_data = []
    marker_colors = {
        'hospital': 'red', 'school': 'blue', 'pharmacy': 'green', 'atm': 'orange', 
        'restaurant': 'purple', 'hotel': 'darkblue', 'college': 'cadetblue',
        'police': 'darkred', 'gym': 'lightgreen', 'bus_station': 'darkgreen',
        'supermarket': 'lightblue'
    }

    for amenity_type in gdf['amenity'].unique():
        filtered_gdf = gdf[gdf['amenity'] == amenity_type]
        nearest_row = None
        nearest_distance = float('inf')

        for _, row in filtered_gdf.iterrows():
            route_coords, route_length = osm_handler.calculate_route(orig_node, row.geometry)

            if route_length <= radius and route_length < nearest_distance:
                nearest_distance = route_length
                nearest_row = row

            if route_coords:
                folium.PolyLine(route_coords, color=marker_colors.get(amenity_type, 'blue'), weight=2.5).add_to(m)

            if isinstance(row.geometry, Point):
                amenity_lat = row.geometry.y
                amenity_lon = row.geometry.x
            elif isinstance(row.geometry, Polygon):
                amenity_lat = row.geometry.centroid.y
                amenity_lon = row.geometry.centroid.x

            folium.CircleMarker(
                location=[amenity_lat, amenity_lon],
                radius=6,
                color=marker_colors.get(amenity_type, 'blue'),
                fill=True,
                tooltip=amenity_type,
                fill_color=marker_colors.get(amenity_type, 'blue'),
                fill_opacity=0.7,
                popup=folium.Popup(f"{amenity_type.capitalize()}", parse_html=True)
            ).add_to(m)

        if nearest_row is not None:
            facility_data.append({
                'Amenity': amenity_type.capitalize(),
                'Nearest Amenity Name': nearest_row.get('name', 'Unnamed'),
                'Distance (meters)': f"{nearest_distance:.0f} meters",
                f'Total Amenities within {radius} meters': len(filtered_gdf)
            })

    df = pd.DataFrame(facility_data)
    return df


def create_map(lat, lon, radius, gdf_amenities=None, graph=None, orig_node=None):
    # Create a Folium map with the default OpenStreetMap tiles
    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="OpenStreetMap")

    # Add a marker for the main location
    folium.Marker(
        location=[lat, lon],
        tooltip="Property Location",
        draggable=False
    ).add_to(m)

    # If amenities data and graph are available, generate the amenities routes and markers
    if gdf_amenities is not None and graph is not None and orig_node is not None:
        facility_df = generate_facility_insights_and_add_routes(m, (lat, lon), gdf_amenities, graph, orig_node, radius)
    else:
        facility_df = pd.DataFrame()

    return m, facility_df


tab1, tab2 = st.tabs(["🗺️ Map", "📋 Table"])

with tab1:
    st.subheader("Map View")

    amenity_options = ['hospital', 'school', 'pharmacy', 'atm', 'restaurant', 'hotel', 'college', 'police', 'gym', 'bus_station', 'supermarket','Airport','Police']
    selected_amenities = st.sidebar.multiselect("Choose Amenities", amenity_options, default=amenity_options)

    if selected_amenities:
        with st.spinner("Fetching amenities..."):
            G, gdf_amenities = fetch_graph_and_amenities(latitude, longitude, radius, selected_amenities)
            osm_handler = OSMHandler((latitude, longitude), radius)
            orig_node = osm_handler.get_nearest_node(latitude, longitude)
    else:
        G, gdf_amenities, orig_node = None, None, None

    with st.spinner("Generating map..."):
        m, facility_df = create_map(latitude, longitude, radius, gdf_amenities, G, orig_node)
        map_data = st_folium(m, width=None, height=650)

with tab2:
    st.subheader("Results")

    if not facility_df.empty:
        st.dataframe(facility_df, use_container_width=True)
    else:
        st.warning("No amenities found or selected within the radius.")

st.markdown("""
### Welcome to the Amenity Finder App!

This application helps you explore different amenities (such as hospitals, schools, pharmacies, ATMs, restaurants, etc.) around a specific location within a radius that you define.

- **Select or Enter a Location**: Use the sidebar to choose a predefined location or enter latitude and longitude manually.
- **Choose Amenities**: Select the types of amenities you're interested in from the list in the sidebar.
- **Adjust the Radius**: Use the slider to define the search radius (in meters).
- **Explore the Map**: The map will display the chosen location, along with routes to the selected amenities.
- **View Insights**: Switch to the "Results" tab to view detailed insights, including the nearest amenity, its distance, and the total number of each type of amenity within the radius.

Enjoy exploring your surroundings!
""")
