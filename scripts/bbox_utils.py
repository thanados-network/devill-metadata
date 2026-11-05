import json

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


def bbox_to_ring(corners):
    """
    Builds the closed ring of (lat, lon) tuples from 2 or 3 (lat, lon) corners.
    2 corners: diagonally opposite corners -> axis-aligned rectangle.
    3 corners: A, B, C with B as the middle corner -> fourth corner D = A + C - B.
    Returns None for invalid input.
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
        a, b, c = corners
        d = (a[0] + c[0] - b[0], a[1] + c[1] - b[1])
        ring = [a, b, c, d]

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
    area2 = sum(
        coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
        for i in range(len(coords) - 1)
    )
    if area2 < 0:
        coords.reverse()
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
