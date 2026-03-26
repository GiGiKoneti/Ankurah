import math

CAMERA_REGISTRY = {
    "CAM-01": {"location_name": "MG Road Junction", "lat": 12.9747, "lng": 77.6094},
    "CAM-02": {"location_name": "Koramangala Market", "lat": 12.9352, "lng": 77.6245},
    "CAM-03": {"location_name": "Indiranagar Metro", "lat": 12.9784, "lng": 77.6408},
    "CAM-04": {"location_name": "Whitefield Main Road", "lat": 12.9698, "lng": 77.7499},
    "CAM-05": {"location_name": "Electronic City Flyover", "lat": 12.8399, "lng": 77.6770},
    "CAM-06": {"location_name": "Jayanagar 4th Block", "lat": 12.9308, "lng": 77.5831},
    "CAM-07": {"location_name": "Rajajinagar Circle", "lat": 12.9889, "lng": 77.5517},
    "CAM-08": {"location_name": "Hebbal Flyover", "lat": 13.0350, "lng": 77.5970},
    "CAM-09": {"location_name": "Silk Board Junction", "lat": 12.9177, "lng": 77.6228},
    "CAM-10": {"location_name": "Bannerghatta Road", "lat": 12.8989, "lng": 77.5975},
    "CAM-11": {"location_name": "Yelahanka New Town", "lat": 13.1007, "lng": 77.5963},
    "CAM-12": {"location_name": "HSR Layout Sector 2", "lat": 12.9116, "lng": 77.6474},
    "CAM-13": {"location_name": "Marathahalli Bridge", "lat": 12.9591, "lng": 77.7009},
    "CAM-14": {"location_name": "Malleshwaram Circle", "lat": 13.0035, "lng": 77.5710},
    "CAM-15": {"location_name": "BTM Layout 2nd Stage", "lat": 12.9166, "lng": 77.6101},
}

POLICE_STATIONS = [
    {"name": "Cubbon Park PS", "phone": "9606076229", "lat": 12.9763, "lng": 77.5929},
    {"name": "MG Road PS", "phone": "9606076229", "lat": 12.9750, "lng": 77.6100},
    {"name": "Indiranagar PS", "phone": "9606076229", "lat": 12.9784, "lng": 77.6408},
    {"name": "Koramangala PS", "phone": "9606076229", "lat": 12.9340, "lng": 77.6270},
    {"name": "HSR Layout PS", "phone": "9606076229", "lat": 12.9116, "lng": 77.6474},
    {"name": "BTM Layout PS", "phone": "9606076229", "lat": 12.9166, "lng": 77.6101},
    {"name": "Jayanagar PS", "phone": "9606076229", "lat": 12.9308, "lng": 77.5831},
    {"name": "Bannerghatta PS", "phone": "9606076229", "lat": 12.8989, "lng": 77.5975},
    {"name": "Electronic City PS", "phone": "9606076229", "lat": 12.8399, "lng": 77.6770},
    {"name": "Whitefield PS", "phone": "9606076229", "lat": 12.9698, "lng": 77.7499},
    {"name": "Marathahalli PS", "phone": "9606076229", "lat": 12.9591, "lng": 77.7009},
    {"name": "Silk Board PS", "phone": "9606076229", "lat": 12.9177, "lng": 77.6228},
    {"name": "Hebbal PS", "phone": "9606076229", "lat": 13.0350, "lng": 77.5970},
    {"name": "Yelahanka PS", "phone": "9606076229", "lat": 13.1007, "lng": 77.5963},
    {"name": "Rajajinagar PS", "phone": "9606076229", "lat": 12.9889, "lng": 77.5517},
    {"name": "Malleshwaram PS", "phone": "9606076229", "lat": 13.0035, "lng": 77.5710},
    {"name": "Seshadripuram PS", "phone": "9606076229", "lat": 12.9921, "lng": 77.5685},
    {"name": "Sadashivanagar PS", "phone": "9606076229", "lat": 13.0102, "lng": 77.5803},
    {"name": "Yeshwanthpur PS", "phone": "9606076229", "lat": 13.0270, "lng": 77.5510},
    {"name": "Wilson Garden PS", "phone": "9606076229", "lat": 12.9497, "lng": 77.5980},
]

def nearest_station(lat: float, lng: float) -> dict:
    """
    Returns the nearest police station dict to the given coordinates.
    Uses Haversine formula to compute great-circle distance.
    """
    def haversine(station: dict) -> float:
        R = 6371  # Earth radius in km
        dlat = math.radians(station["lat"] - lat)
        dlng = math.radians(station["lng"] - lng)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat))
             * math.cos(math.radians(station["lat"]))
             * math.sin(dlng / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))

    return min(POLICE_STATIONS, key=haversine)
