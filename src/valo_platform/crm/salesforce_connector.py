"""Salesforce API connector for OLAV CRM integration."""

import logging
import json
from typing import Optional
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """Connector for Salesforce integration with OLAV."""

    def __init__(
        self,
        instance_url: str,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
    ):
        """Initialize Salesforce connector.

        Args:
            instance_url: Salesforce instance URL (e.g., https://example.salesforce.com)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            username: Salesforce username
            password: Salesforce password (+ security token)
        """
        self.instance_url = instance_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.access_token = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Salesforce using username-password OAuth flow."""
        try:
            auth_url = f"{self.instance_url}/services/oauth2/token"
            payload = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password,
            }

            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("Salesforce authentication successful")
        except requests.RequestException as e:
            logger.error(f"Salesforce authentication failed: {e}")
            raise

    def _headers(self) -> dict:
        """Get HTTP headers for Salesforce API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_opportunity(self, opportunity_id: str) -> dict:
        """Fetch opportunity details.

        Args:
            opportunity_id: Salesforce opportunity ID

        Returns:
            Opportunity dict
        """
        try:
            url = f"{self.instance_url}/services/data/v57.0/sobjects/Opportunity/{opportunity_id}"
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch opportunity {opportunity_id}: {e}")
            return {}

    def get_account(self, account_id: str) -> dict:
        """Fetch account details.

        Args:
            account_id: Salesforce account ID

        Returns:
            Account dict
        """
        try:
            url = f"{self.instance_url}/services/data/v57.0/sobjects/Account/{account_id}"
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch account {account_id}: {e}")
            return {}

    def get_contact(self, contact_id: str) -> dict:
        """Fetch contact details.

        Args:
            contact_id: Salesforce contact ID

        Returns:
            Contact dict
        """
        try:
            url = f"{self.instance_url}/services/data/v57.0/sobjects/Contact/{contact_id}"
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch contact {contact_id}: {e}")
            return {}

    def create_intelligence_record(
        self,
        parent_id: str,
        parent_type: str,
        title: str,
        content: str,
        source: str = "OLAV",
    ) -> Optional[str]:
        """Create OLAV Intelligence record (custom object).

        Args:
            parent_id: Parent Opportunity/Account/Contact ID
            parent_type: Parent object type (Opportunity, Account, Contact)
            title: Intelligence title
            content: Intelligence content
            source: Source identifier (default: OLAV)

        Returns:
            Record ID or None
        """
        try:
            # Create custom object record
            url = f"{self.instance_url}/services/data/v57.0/sobjects/OLAV_Intelligence__c"
            payload = {
                "Title__c": title,
                "Content__c": content,
                "Source__c": source,
                "Captured_At__c": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            }

            # Link to parent object
            if parent_type == "Opportunity":
                payload["Opportunity__c"] = parent_id
            elif parent_type == "Account":
                payload["Account__c"] = parent_id
            elif parent_type == "Contact":
                payload["Contact__c"] = parent_id

            response = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            record_id = response.json().get("id")
            logger.info(f"Created intelligence record {record_id}")
            return record_id
        except requests.RequestException as e:
            logger.error(f"Failed to create intelligence record: {e}")
            return None

    def update_custom_field(
        self,
        sobject_type: str,
        record_id: str,
        field_name: str,
        field_value: str,
    ) -> bool:
        """Update custom field on a record.

        Args:
            sobject_type: Salesforce object type (Opportunity, Account, Contact)
            record_id: Record ID
            field_name: Field name (e.g., OLAV_Intelligence__c)
            field_value: Field value

        Returns:
            Success status
        """
        try:
            url = f"{self.instance_url}/services/data/v57.0/sobjects/{sobject_type}/{record_id}"
            payload = {field_name: field_value}
            response = requests.patch(url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update field: {e}")
            return False

    def query(self, soql: str) -> list:
        """Execute SOQL query.

        Args:
            soql: SOQL query string

        Returns:
            List of records
        """
        try:
            url = f"{self.instance_url}/services/data/v57.0/query"
            params = {"q": soql}
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("records", [])
        except requests.RequestException as e:
            logger.error(f"SOQL query failed: {e}")
            return []

    def create_feed_comment(
        self,
        parent_id: str,
        comment_text: str,
    ) -> Optional[str]:
        """Create comment on Chatter feed.

        Args:
            parent_id: Parent object ID (Opportunity, Account, Contact)
            comment_text: Comment text

        Returns:
            Comment ID or None
        """
        try:
            url = f"{self.instance_url}/services/data/v57.0/sobjects/FeedComment"
            payload = {
                "FeedItemId": parent_id,
                "CommentBody": comment_text,
            }
            response = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("id")
        except requests.RequestException as e:
            logger.error(f"Failed to create feed comment: {e}")
            return None

    def search_opportunities(
        self,
        query_string: str,
        limit: int = 10,
    ) -> list:
        """Search opportunities using SOSL.

        Args:
            query_string: Search query
            limit: Max results

        Returns:
            List of matching opportunities
        """
        soql = f"""
            SELECT Id, Name, StageName, Amount, CloseDate
            FROM Opportunity
            WHERE Name LIKE '%{query_string}%'
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """
        return self.query(soql)

    def get_opportunities_by_account(self, account_id: str) -> list:
        """Get all opportunities for an account.

        Args:
            account_id: Account ID

        Returns:
            List of opportunities
        """
        soql = f"""
            SELECT Id, Name, StageName, Amount, CloseDate
            FROM Opportunity
            WHERE AccountId = '{account_id}'
            ORDER BY CloseDate DESC
        """
        return self.query(soql)

    def get_intelligence_for_record(
        self,
        record_id: str,
        object_type: str = "Opportunity",
    ) -> list:
        """Get OLAV intelligence records for a parent object.

        Args:
            record_id: Parent record ID
            object_type: Parent object type

        Returns:
            List of intelligence records
        """
        field_map = {
            "Opportunity": "Opportunity__c",
            "Account": "Account__c",
            "Contact": "Contact__c",
        }
        field = field_map.get(object_type, "Opportunity__c")

        soql = f"""
            SELECT Id, Title__c, Content__c, Captured_At__c
            FROM OLAV_Intelligence__c
            WHERE {field} = '{record_id}'
            ORDER BY Captured_At__c DESC
            LIMIT 50
        """
        return self.query(soql)
