from dataclasses import dataclass

from vocal.constants import ISO3166Country


@dataclass
class Address:
    country: ISO3166Country
