"""
Data models for the Multi-Source Web Scraping Pipeline.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


@dataclass
class StandardRecord:
    """Standardized schema representing an entity across heterogeneous sources.

    Complies with section 5.2 and 8 of the assessment specification.
    """
    source: str
    source_url: str
    name_or_title: str
    category: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    availability: Optional[str] = None
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    is_duplicate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary for CSV/JSON export matching the required schema."""
        return {
            "source": self.source,
            "name_or_title": self.name_or_title,
            "category": self.category if self.category is not None else "",
            "price": self.price if self.price is not None else "",
            "rating": self.rating if self.rating is not None else "",
            "author": self.author if self.author is not None else "",
            "tags": self.tags if self.tags is not None else "",
            "description": self.description if self.description is not None else "",
            "availability": self.availability if self.availability is not None else "",
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "is_duplicate": self.is_duplicate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardRecord":
        """Instantiate a StandardRecord from a dictionary."""
        return cls(
            source=data.get("source", ""),
            source_url=data.get("source_url", ""),
            name_or_title=data.get("name_or_title", ""),
            category=data.get("category"),
            price=data.get("price"),
            rating=data.get("rating"),
            author=data.get("author"),
            tags=data.get("tags"),
            description=data.get("description"),
            availability=data.get("availability"),
            scraped_at=data.get(
                "scraped_at",
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            is_duplicate=bool(data.get("is_duplicate", False)),
        )

    @staticmethod
    def get_field_names(include_duplicate_flag: bool = True) -> List[str]:
        """Returns standard column names in preferred order."""
        fields = [
            "source",
            "name_or_title",
            "category",
            "price",
            "rating",
            "author",
            "tags",
            "description",
            "availability",
            "source_url",
            "scraped_at",
        ]
        if include_duplicate_flag:
            fields.append("is_duplicate")
        return fields
