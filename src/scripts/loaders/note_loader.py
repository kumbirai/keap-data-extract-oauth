"""
Specialized loader for notes.

Notes have relationships with contacts and specific attributes like type,
body content, and custom field values that need special handling.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.entity_models import NoteType
from src.models.models import Contact
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class NoteLoader(BaseEntityLoader):
    """Specialized loader for notes with relationship handling.
    
    Notes are unique because:
    1. They have relationships with contacts that need to be properly linked
    2. They have various types (Call, Email, Meeting, etc.) that need validation
    3. They have body content that may need processing or validation
    4. They have custom field values that need to be processed
    5. They may have rich text content that needs special handling
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "notes", "get_notes", "get_note")

    def _process_entity(self, note: Any) -> None:
        """Process note-specific relationships and attributes.
        
        This method handles the complex relationships and attributes that notes have:
        - Contact relationships
        - Note type validation
        - Body content processing
        - Custom field values
        """
        # Handle contact relationships
        if hasattr(note, 'contacts'):
            # Ensure all referenced contacts exist in the database
            self._ensure_contacts_exist(note.contacts)
            note.contacts = note.contacts

        # Handle primary contact relationship
        if hasattr(note, 'contact_id') and note.contact_id:
            self._ensure_primary_contact_exists(note.contact_id)

        # Validate and process note attributes
        self._process_note_attributes(note)

        # Handle note content and type
        self._process_note_content(note)

        # Handle custom field values
        if hasattr(note, 'custom_field_values'):
            note.custom_field_values = note.custom_field_values

    def _ensure_contacts_exist(self, contacts: list) -> None:
        """Ensure all referenced contacts exist in the database, creating stubs if needed."""
        if not contacts:
            return
        for contact in contacts:
            if not getattr(contact, 'id', None):
                continue
            self._ensure_entity_exists(Contact, contact.id)

    def _ensure_primary_contact_exists(self, contact_id: int) -> None:
        """Ensure the primary contact for a note exists in the database, creating a stub if needed."""
        self._ensure_entity_exists(Contact, contact_id)

    def _normalize_note_type(self, raw_type: Any) -> Optional[NoteType]:
        """Convert a raw type value to a NoteType enum member, or None if unrecognized."""
        if raw_type is None:
            return None
        if isinstance(raw_type, NoteType):
            return raw_type
        # Exact value match
        for member in NoteType:
            if member.value == raw_type:
                return member
        # Case-insensitive value match
        raw_upper = str(raw_type).upper()
        for member in NoteType:
            if member.value.upper() == raw_upper:
                return member
        logger.warning(f"Unrecognized note type '{raw_type}' - setting to None")
        return None

    def _process_note_attributes(self, note: Any) -> None:
        """Process and validate note-specific attributes.
        
        This method handles note type, title, and other attributes
        with appropriate validation and logging.
        """
        # Normalize note type to enum member (or None if unrecognized)
        if hasattr(note, 'type'):
            normalized = self._normalize_note_type(note.type)
            if normalized != note.type:
                logger.debug(f"Note {note.id}: normalizing type '{note.type}' -> {normalized}")
            note.type = normalized

        # Log title information
        if hasattr(note, 'title') and note.title:
            logger.debug(f"Processing note {note.id} with title: {note.title}")
        elif hasattr(note, 'title') and not note.title:
            logger.debug(f"Note {note.id} has no title")

        # Process creation and modification dates
        if hasattr(note, 'created_at') and note.created_at:
            logger.debug(f"Note {note.id} was created on: {note.created_at}")

        if hasattr(note, 'modified_at') and note.modified_at:
            logger.debug(f"Note {note.id} was modified on: {note.modified_at}")

    def _process_note_content(self, note: Any) -> None:
        """Process note content like body text."""
        # Process note body
        if hasattr(note, 'body') and note.body:
            try:
                # Log body length for debugging
                body_length = len(note.body) if note.body else 0
                logger.debug(f"Note {note.id} has body with {body_length} characters")

                # Could add content validation here (e.g., check for required fields)
                # Could add content processing here (e.g., HTML sanitization, link extraction)
                self._process_body_content(note.body)

            except Exception as e:
                logger.warning(f"Error processing body for note {note.id}: {str(e)}")
        elif hasattr(note, 'body') and not note.body:
            logger.debug(f"Note {note.id} has no body content")

    def _process_body_content(self, body: str) -> None:
        """Process the body content of a note.
        
        This method can be extended to handle various content processing needs:
        - HTML sanitization
        - Link extraction
        - Content validation
        - Text analysis
        """
        try:
            # Basic content analysis
            if body:
                # Check for common patterns
                if '<' in body and '>' in body:
                    logger.debug("Note body contains HTML-like content")

                if 'http' in body:
                    logger.debug("Note body contains URLs")

                # Could add more sophisticated content processing here  # For example: sentiment analysis, keyword extraction, etc.

        except Exception as e:
            logger.warning(f"Error in body content processing: {str(e)}")

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to notes."""
        return {'id': item.id, 'title': getattr(item, 'title', None), 'type': getattr(item, 'type', None), 'contact_id': getattr(item, 'contact_id', None),
                'body_length': len(getattr(item, 'body', '')) if getattr(item, 'body', None) else 0, 'created_at': getattr(item, 'created_at', None), 'modified_at': getattr(item, 'modified_at', None)}

