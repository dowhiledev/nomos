# from dotenv import load_dotenv
# load_dotenv()

import os
import requests
from typing import List, Literal, Optional

from models import Listing, DetailedListing, to_listing


# Allowed property types
PropertyType = Literal[
    "All",
    "Detached",
    "Semi-Detached",
    "Freehold Townhouse",
    "Condo Townhouse",
    "Condo Apt",
    "Multiplex",
    "Vacant Land",
]

# Basement types
BasementType = Literal["All", "Finished", "Walkout", "Seperate Entrance"]

# Listing status
Status = Literal["Active", "Sold", "All"]

# Period for sold/delisted status, e.g.: last 7 days, 90 days, etc.
Period = Literal["7D", "90D", "All"]

# Integer or the literal "5+" for upper bound filters
FivePlusInt = Literal[1, 2, 3, 4, "5+", "All"]

# Sort options for listings
SortBy = Literal[
    "Default", "Newest", "Oldest", "Price Low to High", "Price High to Low"
]


class RepliersAPI:
    def __init__(self, num_results_per_page: int = 15):
        REPLIERS_API_KEY = os.getenv("REPLIERS_API_KEY")
        assert REPLIERS_API_KEY, (
            "REPLIERS_API_KEY must be set in the environment variables"
        )
        self.headers = {
            "REPLIERS-API-KEY": REPLIERS_API_KEY,
            "Content-Type": "application/json",
        }
        self.base_url = "https://api.repliers.io"
        self.num_results_per_page = num_results_per_page

    def get_listings(
        self,
        area: Optional[str] = None,
        city: Optional[List[str]] = None,
        district: Optional[str] = None,
        property_types: Optional[list[PropertyType]] = None,
        status: Optional[Status] = None,
        # status_period: Optional[Period] = None,
        bedrooms: Optional[List[FivePlusInt]] = None,
        bathrooms: Optional[List[FivePlusInt]] = None,
        den: Optional[Literal["Yes", "No", "All"]] = None,
        parking: Optional[List[FivePlusInt]] = None,
        keyword: Optional[str] = None,
        basement: Optional[BasementType] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        max_maintenance_fee: Optional[int] = None,
        min_sqft: Optional[int] = None,
        max_sqft: Optional[int] = None,
        sort_by: Optional[SortBy] = None,
        page_num: int = 1,
    ) -> list[Listing]:
        """Fetch listings."""

        params = {
            "listings": "true",
            "operator": "AND",
            "resultsPerPage": 15,
            "pageNum": page_num,
        }
        if area:
            params["area"] = area
        if city:
            params["city"] = city
        if district:
            params["district"] = district
        if sort_by:
            if sort_by == "Newest":
                params["sortBy"] = "updatedOnDesc"
            elif sort_by == "Oldest":
                params["sortBy"] = "updatedOnAsc"
            elif sort_by == "Price Low to High":
                params["sortBy"] = "listPriceAsc"
            elif sort_by == "Price High to Low":
                params["sortBy"] = "listPriceDesc"
            else:
                params["sortBy"] = "updatedOnDesc"
        else:
            params["sortBy"] = "updatedOnDesc"
        if property_types and "All" not in property_types:
            params["propertyType"] = property_types
        if status and status != "All":
            params["status"] = (
                ["A"]
                if status == "Active"
                else ["U"]
                if status == "Sold"
                else ["A", "U"]
            )
        # if status_period and status_period != "All":
        #     params["statusPeriod"] = status_period
        if bedrooms and "All" not in bedrooms:
            if "5+" in bedrooms:
                params["minBedrooms"] = 5
            else:
                params["minBedrooms"] = min(bedrooms)
                params["maxBedrooms"] = max(bedrooms)
        if bathrooms and "All" not in bathrooms:
            if "5+" in bathrooms:
                params["minBathrooms"] = 5
            else:
                params["minBathrooms"] = min(bathrooms)
                params["maxBathrooms"] = max(bathrooms)
        if den and den != "All":
            params["den"] = den == "Yes"
        if parking and "All" not in parking:
            if "5+" in parking:
                params["minParking"] = 5
            else:
                params["minParking"] = min(parking)
                params["maxParking"] = max(parking)
        if keyword:
            params["search"] = keyword
        if basement and basement != "All":
            params["basement"] = basement
        if min_price is not None:
            params["minPrice"] = min_price
        if max_price is not None:
            params["maxPrice"] = max_price
        if max_maintenance_fee is not None:
            params["maxMaintenanceFee"] = max_maintenance_fee
        if min_sqft is not None:
            params["minSqft"] = min_sqft
        if max_sqft is not None:
            params["maxSqft"] = max_sqft

        # Make the API request
        response = requests.post(
            f"{self.base_url}/listings", headers=self.headers, params=params
        )
        response.raise_for_status()  # Raise an error for bad responses
        listings = response.json().get("listings", [])
        return [
            Listing(
                mls_number=listing.get("mlsNumber"),
                list_price=listing.get("listPrice"),
                board_id=listing.get("boardId"),
                url=f"https://zown.ca/{listing.get('mlsNumber')}",
                is_sold=listing.get("lastStatus") == "Sld"
            )
            for listing in listings
        ]

    def get_listing_details(
        self, mls_number: str, board_id: Optional[int] = None
    ) -> DetailedListing:
        """Fetch details for a specific listing by its ID."""
        response = requests.get(
            f"{self.base_url}/listings/{mls_number}",
            headers=self.headers,
            params={"boardId": board_id} if board_id else {},
        )
        response.raise_for_status()  # Raise an error for bad responses
        return to_listing(response.json())

    def get_listing_comparables(
        self, mls_number: str, board_id: Optional[int] = None
    ) -> list[Listing]:
        """Fetch comparables for a specific listing by its ID."""
        response = requests.get(
            f"{self.base_url}/listings/{mls_number}",
            headers=self.headers,
            params={"boardId": board_id} if board_id else {},
        )
        response.raise_for_status()  # Raise an error for bad responses
        comparables = response.json().get("comparables", [])
        return [
            Listing(
                mls_number=comp.get("mlsNumber"),
                list_price=comp.get("listPrice"),
                board_id=comp.get("boardId") or board_id,
                url=f"https://zown.ca/{comp.get('mlsNumber')}",
                is_sold=comp.get("lastStatus") == "Sld"
            )
            for comp in comparables
        ]

repliers_api = RepliersAPI(num_results_per_page=10)

tools = [
    repliers_api.get_listing_comparables,
    repliers_api.get_listing_details,
    repliers_api.get_listings,
]

# if __name__ == "__main__":
#     # Example usage of the RepliersAPI
#     repliers_api = RepliersAPI(num_results_per_page=10)
#     # Example usage
#     result = repliers_api.get_listings(
#         property_types=["Detached", "Condo Apt"], bedrooms=[3]
#     )
#     print(result[0])
#     # Example usage of get_listing_details
#     listing_details = repliers_api.get_listing_details(
#         result[0].mls_number, result[0].board_id
#     )
#     print(listing_details)
#     # Example usage of get_listing_comparables
#     comparables = repliers_api.get_listing_comparables(
#         result[0].mls_number, result[0].board_id
#     )
#     print(comparables)
