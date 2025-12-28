"""Parser registry for linkfeed."""

from linkfeed.parsers.base import BaseParser, get_parser
from linkfeed.parsers.generic import GenericParser
from linkfeed.parsers.youtube import YouTubeParser
from linkfeed.parsers.media import MediaParser

__all__ = ["BaseParser", "get_parser", "GenericParser", "YouTubeParser", "MediaParser"]
