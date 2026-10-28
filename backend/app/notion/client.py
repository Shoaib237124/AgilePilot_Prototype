import os
import requests


NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
MAX_BLOCKS_PER_REQUEST = 100


class NotionError(Exception):
    pass


class NotionClient:

    def __init__(self):

        self.api_key = os.getenv("NOTION_API_KEY")
        self.parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")

        if not self.api_key:
            raise NotionError(
                "NOTION_API_KEY is not configured."
            )

        if not self.parent_page_id:
            raise NotionError(
                "NOTION_PARENT_PAGE_ID is not configured."
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def create_page(
        self,
        title: str,
        blocks: list
    ):
        """
        Create a Notion page and add all blocks.

        Notion allows a maximum of 100 children
        in a single request, so blocks are split
        into batches automatically.
        """

        first_batch = blocks[:MAX_BLOCKS_PER_REQUEST]
        remaining_blocks = blocks[MAX_BLOCKS_PER_REQUEST:]

        payload = {
            "parent": {
                "page_id": self.parent_page_id
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            },
            "children": first_batch
        }

        response = requests.post(
            f"{NOTION_API_URL}/pages",
            headers=self.headers,
            json=payload,
            timeout=30
        )

        if not response.ok:
            raise NotionError(
                f"Notion page creation failed: "
                f"{response.status_code} {response.text}"
            )

        page = response.json()

        page_id = page.get("id")

        if not page_id:
            raise NotionError(
                "Notion page was created but no page ID was returned."
            )

        # Append remaining blocks in batches of 100
        for i in range(
            0,
            len(remaining_blocks),
            MAX_BLOCKS_PER_REQUEST
        ):

            batch = remaining_blocks[
                i:i + MAX_BLOCKS_PER_REQUEST
            ]

            self.append_blocks(
                page_id,
                batch
            )

        return page

    def append_blocks(
        self,
        page_id: str,
        blocks: list
    ):
        """
        Append blocks to an existing Notion page.

        Automatically splits blocks into batches
        of maximum 100.
        """

        for i in range(
            0,
            len(blocks),
            MAX_BLOCKS_PER_REQUEST
        ):

            batch = blocks[
                i:i + MAX_BLOCKS_PER_REQUEST
            ]

            response = requests.patch(
                f"{NOTION_API_URL}/blocks/{page_id}/children",
                headers=self.headers,
                json={
                    "children": batch
                },
                timeout=30
            )

            if not response.ok:
                raise NotionError(
                    f"Notion block append failed: "
                    f"{response.status_code} {response.text}"
                )