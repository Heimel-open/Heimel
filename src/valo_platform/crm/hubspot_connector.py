"""HubSpot API connector for OLAV CRM integration."""

import logging
from typing import Optional
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

HUBSPOT_API_URL = "https://api.hubapi.com"


class HubSpotConnector:
    """Connector for HubSpot integration with OLAV."""

    def __init__(self, api_key: str):
        """Initialize HubSpot connector.

        Args:
            api_key: HubSpot private app access token
        """
        self.api_key = api_key
        self._verify_connection()

    def _headers(self) -> dict:
        """Get HTTP headers for HubSpot API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _verify_connection(self) -> None:
        """Verify HubSpot connection."""
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/contacts"
            params = {"limit": 1}
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            response.raise_for_status()
            logger.info("HubSpot connection verified")
        except requests.RequestException as e:
            logger.warning(f"HubSpot connection verification failed: {e}")

    def get_deal(self, deal_id: str) -> dict:
        """Fetch deal details.

        Args:
            deal_id: HubSpot deal ID

        Returns:
            Deal dict with properties
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/deals/{deal_id}"
            params = {
                "properties": [
                    "dealname",
                    "dealstage",
                    "amount",
                    "closedate",
                    "hs_analytics_num_page_views",
                ]
            }
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch deal {deal_id}: {e}")
            return {}

    def get_contact(self, contact_id: str) -> dict:
        """Fetch contact details.

        Args:
            contact_id: HubSpot contact ID

        Returns:
            Contact dict with properties
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/contacts/{contact_id}"
            params = {
                "properties": [
                    "firstname",
                    "lastname",
                    "email",
                    "phone",
                    "lifecyclestage",
                ]
            }
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch contact {contact_id}: {e}")
            return {}

    def get_company(self, company_id: str) -> dict:
        """Fetch company details.

        Args:
            company_id: HubSpot company ID

        Returns:
            Company dict with properties
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/companies/{company_id}"
            params = {
                "properties": [
                    "name",
                    "industry",
                    "annualrevenue",
                    "numberofemployees",
                ]
            }
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch company {company_id}: {e}")
            return {}

    def create_intelligence_note(
        self,
        object_id: str,
        object_type: str,
        title: str,
        content: str,
    ) -> Optional[str]:
        """Create intelligence note as custom property or note.

        Args:
            object_id: HubSpot object ID
            object_type: Object type (deals, contacts, companies)
            title: Note title
            content: Note content

        Returns:
            Note ID or None
        """
        try:
            # Create custom property value update
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/{object_type}/{object_id}"

            # Build custom property name
            prop_name = "olav_intelligence"
            note_value = f"{title}\n\n{content}\n\n[Captured: {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}]"

            payload = {
                "properties": {
                    prop_name: note_value,
                }
            }

            response = requests.patch(url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Created intelligence note for {object_type}/{object_id}")
            return f"{object_type}/{object_id}/notes"
        except requests.RequestException as e:
            logger.error(f"Failed to create intelligence note: {e}")
            return None

    def create_activity(
        self,
        object_id: str,
        object_type: str,
        activity_type: str,
        title: str,
        notes: str,
    ) -> Optional[str]:
        """Create activity/engagement record.

        Args:
            object_id: HubSpot object ID
            object_type: Object type (deals, contacts, companies)
            activity_type: Activity type (task, email, meeting, note, call)
            title: Activity title
            notes: Activity notes

        Returns:
            Activity ID or None
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/activities"

            payload = {
                "properties": {
                    "hs_activity_type": activity_type,
                    "hs_activity_subject": title,
                    "hs_activity_notes": notes,
                    "hs_timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                },
                "associations": [
                    {
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationType": f"{object_type}_to_activity"}],
                        "id": object_id,
                    }
                ],
            }

            response = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            activity_id = response.json().get("id")
            logger.info(f"Created activity {activity_id}")
            return activity_id
        except requests.RequestException as e:
            logger.error(f"Failed to create activity: {e}")
            return None

    def search_deals(
        self,
        query_string: str,
        limit: int = 10,
    ) -> list:
        """Search deals.

        Args:
            query_string: Search query
            limit: Max results

        Returns:
            List of matching deals
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/deals"
            params = {
                "limit": limit,
                "properties": ["dealname", "dealstage", "amount"],
                "after": "0",
            }

            # Use search endpoint if available
            search_url = f"{HUBSPOT_API_URL}/crm/v3/objects/deals/search"
            payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "dealname",
                                "operator": "CONTAINS_TOKEN",
                                "value": query_string,
                            }
                        ]
                    }
                ],
                "limit": limit,
                "properties": ["dealname", "dealstage", "amount"],
            }

            response = requests.post(search_url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("results", [])
        except requests.RequestException as e:
            logger.error(f"Deal search failed: {e}")
            return []

    def get_deals_for_company(self, company_id: str, limit: int = 50) -> list:
        """Get all deals associated with a company.

        Args:
            company_id: Company ID
            limit: Max results

        Returns:
            List of deals
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/companies/{company_id}/associations/deals"
            params = {"limit": limit}
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            response.raise_for_status()
            associations = response.json().get("results", [])

            # Fetch deal details for each association
            deals = []
            for assoc in associations:
                deal_id = assoc.get("id")
                deal = self.get_deal(deal_id)
                if deal:
                    deals.append(deal)
            return deals
        except requests.RequestException as e:
            logger.error(f"Failed to get company deals: {e}")
            return []

    def update_custom_property(
        self,
        object_id: str,
        object_type: str,
        property_name: str,
        property_value: str,
    ) -> bool:
        """Update custom property on a record.

        Args:
            object_id: HubSpot object ID
            object_type: Object type (deals, contacts, companies)
            property_name: Property name
            property_value: Property value

        Returns:
            Success status
        """
        try:
            url = f"{HUBSPOT_API_URL}/crm/v3/objects/{object_type}/{object_id}"
            payload = {
                "properties": {
                    property_name: property_value,
                }
            }
            response = requests.patch(url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update property: {e}")
            return False

    def get_intelligence_history(
        self,
        object_id: str,
        object_type: str = "deals",
    ) -> dict:
        """Get OLAV intelligence history for a record.

        Args:
            object_id: HubSpot object ID
            object_type: Object type

        Returns:
            Intelligence dict with history
        """
        try:
            obj = self.get_deal(object_id) if object_type == "deals" else self.get_contact(object_id)
            if not obj:
                return {}

            properties = obj.get("properties", {})
            intelligence_value = properties.get("olav_intelligence", "")

            return {
                "object_id": object_id,
                "object_type": object_type,
                "intelligence": intelligence_value,
                "captured_at": properties.get("olav_intelligence_updated_at", ""),
            }
        except Exception as e:
            logger.error(f"Failed to get intelligence history: {e}")
            return {}
