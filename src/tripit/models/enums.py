"""Enums for TripIt v1 API restricted-string types.

These mirror the `xs:enumeration` constraints from the XSD. Model fields keep
their base type (`str`) for forward-compatibility; these enums expose the known
values as constants for callers that want exhaustive matches.
"""

from __future__ import annotations

from enum import StrEnum


class FlightStatusCode(StrEnum):
    """Encoded flight status returned by TripIt Pro `AirSegment.Status`."""

    NOT_MONITORABLE = "100"
    NOT_MONITORED = "200"
    SCHEDULED = "300"
    ON_TIME = "301"
    IN_FLIGHT_ON_TIME = "302"
    ARRIVED_ON_TIME = "303"
    CANCELLED = "400"
    DELAYED = "401"
    IN_FLIGHT_LATE = "402"
    ARRIVED_LATE = "403"
    DIVERTED = "404"
    POSSIBLY_DELAYED = "405"
    IN_FLIGHT_POSSIBLY_LATE = "406"
    ARRIVED_POSSIBLY_LATE = "407"
    UNKNOWN = "408"


class TripPurposeTypeCode(StrEnum):
    """`TripPurposes.purpose_type_code`."""

    BUSINESS = "B"
    LEISURE = "L"


class ActivityDetailTypeCode(StrEnum):
    """`ActivityObject.detail_type_code`."""

    CONCERT = "C"
    THEATER = "H"
    MEETING = "M"
    TOUR = "T"


class NoteDetailTypeCode(StrEnum):
    """`NoteObject.detail_type_code`."""

    ARTICLE = "A"


class DirectionsDetailTypeCode(StrEnum):
    """`DirectionsObject.detail_type_code`."""

    BICYCLING = "B"
    DRIVING = "D"
    TRANSIT = "T"
    WALKING = "W"


class TransportDetailTypeCode(StrEnum):
    """`TransportSegment.detail_type_code`."""

    FERRY = "F"
    GROUND = "G"


class CruiseDetailTypeCode(StrEnum):
    """`CruiseSegment.detail_type_code`."""

    PORT_OF_CALL = "P"


class ImageMimeType(StrEnum):
    """`ImageData.mime_type`."""

    JPEG = "image/jpeg"
    PJPEG = "image/pjpeg"
    CITRIX_PJPEG = "image/x-citrix-pjpeg"
    PNG = "image/png"
    X_PNG = "image/x-png"
    GIF = "image/gif"
    PDF = "application/pdf"


class SeatPreference(StrEnum):
    """`SeatTrackerCriteria.seat_preferences` entry."""

    WINDOW = "window"
    AISLE = "aisle"
    MIDDLE = "middle"


class AreaPreference(StrEnum):
    """`SeatTrackerCriteria.area_preferences` entry."""

    OVER_WING = "over_wing"
    AHEAD_OF_WING = "ahead_of_wing"
    BEHIND_WING = "behind_wing"
