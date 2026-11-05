import json
import math

WKT_LITERAL_DATATYPE = 'http://www.opengis.net/ont/geosparql#wktLiteral'


def parse_bounding_box(raw):
    """
    Parses a bounding box given as JSON text or list: [[lat, lon], [lat, lon](, [lat, lon])].
    Returns a list of (lat, lon) tuples with 2 or 3 corners, or None if invalid.
    """
    if raw is None:
        return None

    data = raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode('utf-8', errors='replace')
    if isinstance(raw, str):
        if not raw.strip():
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            return None

    if not isinstance(data, (list, tuple)) or len(data) not in (2, 3):
        return None

    corners = []
    for point in data:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        try:
            lat, lon = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        corners.append((lat, lon))
    return corners


def _fmt(value):
    return format(value, '.10f').rstrip('0').rstrip('.')


def _to_mercator(lat, lon):
    """Projects (lat, lon) to Web Mercator (EPSG:3857 units, scaled to a unit sphere), as Leaflet does."""
    return math.radians(lon), math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _from_mercator(x, y):
    """Inverse of _to_mercator, returns (lat, lon)."""
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2), math.degrees(x)


def bbox_to_ring(corners):
    """
    Builds the closed ring of (lat, lon) tuples that outlines the image, following the
    Leaflet conventions. The exterior ring is oriented counterclockwise (lon/lat plane).
    Returns None for invalid input.

    2 corners: L.imageOverlay bounds. Any two diagonally opposite corners (south-west and
        north-east) span an axis-aligned rectangle (edges along parallels and meridians).
    3 corners: leaflet.imageoverlay.rotated, in the order [topleft, topright, bottomleft].
        The fourth corner is bottomright = topright + bottomleft - topleft, calculated in
        the projected (Web Mercator) plane as the plugin does when it draws the image.
        The ring runs topleft, topright, bottomright, bottomleft.
    """
    if not corners or len(corners) not in (2, 3):
        return None

    if len(corners) == 2:
        (lat1, lon1), (lat2, lon2) = corners
        lat_min, lat_max = min(lat1, lat2), max(lat1, lat2)
        lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
        ring = [
            (lat_min, lon_min),
            (lat_min, lon_max),
            (lat_max, lon_max),
            (lat_max, lon_min),
        ]
    else:
        top_left, top_right, bottom_left = corners
        try:
            tlx, tly = _to_mercator(*top_left)
            trx, try_ = _to_mercator(*top_right)
            blx, bly = _to_mercator(*bottom_left)
        except (ValueError, OverflowError):
            return None
        bottom_right = _from_mercator(trx + blx - tlx, try_ + bly - tly)
        ring = [top_left, top_right, bottom_right, bottom_left]

    area2 = sum(
        ring[i][1] * ring[(i + 1) % 4][0] - ring[(i + 1) % 4][1] * ring[i][0]
        for i in range(4)
    )
    if area2 == 0:
        return None
    if area2 < 0:
        ring.reverse()

    ring.append(ring[0])
    return ring


def bbox_to_wkt(corners):
    """
    Builds a closed WKT POLYGON (order: lon lat) from 2 or 3 (lat, lon) corners.
    Returns None for invalid input.
    """
    ring = bbox_to_ring(corners)
    if ring is None:
        return None
    points = ', '.join(f"{_fmt(lon)} {_fmt(lat)}" for lat, lon in ring)
    return f"POLYGON(({points}))"


def bbox_to_geojson_geometry(corners):
    """
    Builds a GeoJSON Polygon geometry (order: lon, lat; exterior ring counterclockwise
    as required by RFC 7946) from 2 or 3 (lat, lon) corners. Returns None for invalid input.
    """
    ring = bbox_to_ring(corners)
    if ring is None:
        return None
    coords = [[float(_fmt(lon)), float(_fmt(lat))] for lat, lon in ring]
    return {"type": "Polygon", "coordinates": [coords]}


def load_bounding_boxes(cur):
    """
    Loads bounding boxes from web.map_overlay.
    Returns {image_id: {'raw': str, 'wkt': str, 'geometry': GeoJSON Polygon dict}}. Invalid entries are skipped with a warning.
    """
    result = {}
    try:
        cur.execute("SELECT image_id, bounding_box FROM web.map_overlay;")
        rows = cur.fetchall()
    except Exception as e:
        print(f"Warning: Could not read web.map_overlay: {e}")
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return result

    for image_id, raw in rows:
        corners = parse_bounding_box(raw)
        wkt = bbox_to_wkt(corners)
        if wkt is None:
            print(f"Warning: Skipping invalid bounding_box for image_id {image_id}: {raw!r}")
            continue
        raw_text = raw if isinstance(raw, str) else json.dumps(raw)
        result[image_id] = {'raw': raw_text, 'wkt': wkt, 'geometry': bbox_to_geojson_geometry(corners)}
    return result
