"""Keap API client with all entity endpoints."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .base_client import KeapBaseClient
from .exceptions import KeapNotFoundError

logger = logging.getLogger(__name__)

# Import transformers and models - these will be available after they're ported
try:
    from src.transformers.transformers import (
        transform_account_profile, transform_affiliate, transform_affiliate_clawback,
        transform_affiliate_commission, transform_affiliate_payment, transform_affiliate_program,
        transform_affiliate_redirect, transform_affiliate_summary, transform_applied_tag,
        transform_campaign, transform_contact_with_related, transform_credit_card,
        transform_custom_field, transform_list_response, transform_note, transform_opportunity,
        transform_order_item, transform_order_payment, transform_order_transaction,
        transform_order_with_items, transform_payment_gateway, transform_payment_plan,
        transform_product, transform_subscription, transform_tag, transform_task
    )
    from src.models.models import (
        AccountProfile, Affiliate, AffiliateClawback, AffiliateCommission, AffiliatePayment,
        AffiliateProgram, AffiliateRedirect, AffiliateSummary, Campaign, Contact, CustomField,
        Note, Opportunity, Order, OrderItem, OrderPayment, OrderTransaction, Product,
        Subscription, Tag, Task
    )
except ImportError:
    # Placeholder imports for when transformers/models aren't ready yet
    logger.warning("Transformers or models not yet available - some functionality may be limited")
    transform_list_response = lambda x, y: ([], {})
    transform_contact_with_related = lambda x, y=None: None
    transform_opportunity = lambda x: None
    transform_product = lambda x: None
    transform_order_with_items = lambda x: None
    transform_order_item = lambda x: None
    transform_order_payment = lambda x: None
    transform_order_transaction = lambda x: None
    transform_payment_plan = lambda x, y: None
    transform_payment_gateway = lambda x: None
    transform_task = lambda x: None
    transform_note = lambda x: None
    transform_campaign = lambda x: None
    transform_subscription = lambda x: None
    transform_account_profile = lambda x: None
    transform_affiliate = lambda x: None
    transform_affiliate_commission = lambda x: None
    transform_affiliate_program = lambda x: None
    transform_affiliate_redirect = lambda x: None
    transform_affiliate_summary = lambda x: None
    transform_affiliate_clawback = lambda x: None
    transform_affiliate_payment = lambda x: None
    transform_tag = lambda x: None
    transform_applied_tag = lambda x: None
    transform_custom_field = lambda x, y: None
    transform_credit_card = lambda x: None
    Contact = None
    Opportunity = None
    Product = None
    Order = None
    OrderItem = None
    OrderPayment = None
    OrderTransaction = None
    Task = None
    Note = None
    Campaign = None
    Subscription = None
    AccountProfile = None
    Affiliate = None
    AffiliateCommission = None
    AffiliateProgram = None
    AffiliateRedirect = None
    AffiliateSummary = None
    AffiliateClawback = None
    AffiliatePayment = None
    Tag = None
    CustomField = None


class KeapClient(KeapBaseClient):
    """Keap API client with all entity endpoints."""
    
    def __init__(self, token_manager=None, db_session=None):
        """Initialize Keap API client.
        
        Args:
            token_manager: Optional TokenManager instance. If not provided, one will be created.
            db_session: Optional database session. Required if token_manager is not provided.
        """
        from src.auth.token_manager import TokenManager
        from src.database.config import SessionLocal
        
        if token_manager is None:
            if db_session is None:
                db_session = SessionLocal()
            token_manager = TokenManager(db_session)
        
        super().__init__(token_manager)
    
    # Core/Utility Methods
    def _parse_next_url(self, next_url: Optional[str]) -> Optional[int]:
        """Parse the offset from a next URL.
        
        Args:
            next_url: The next URL from the API response
            
        Returns:
            The offset value from the URL, or None if not found
        """
        if not next_url:
            return None

        try:
            parsed_url = urlparse(next_url)
            query_params = parse_qs(parsed_url.query)
            offset = query_params.get('offset', [None])[0]
            return int(offset) if offset is not None else None
        except (ValueError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse next URL: {next_url}. Error: {str(e)}")
            return None

    def _prepare_params(self, limit: int = 50, offset: int = 0, order: str = None, **additional_params) -> Dict[str, Any]:
        """Prepare parameters for API requests.
        
        Args:
            limit: Maximum number of items to return
            offset: Offset for pagination
            order: Field to order by (default varies by endpoint)
            additional_params: Additional parameters to include
            
        Returns:
            Dictionary of parameters for the API request
        """
        # Start with additional_params as base
        params = additional_params.copy()

        # Override with explicit parameters if they are not None
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset

        # Only include order parameter if it's explicitly provided
        # This is because some endpoints don't support ordering
        # and others have specific default ordering
        if order is not None:
            params['order'] = order

        # Filter out None values
        params = {k: v for k, v in params.items() if v is not None}

        return params

    # Contact Related Methods
    def get_contacts(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of contacts.
        
        Args:
            limit: Maximum number of contacts to return
            offset: Offset for pagination
            since: Optional timestamp to get contacts modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Contact objects
            - Dictionary containing pagination metadata
        """
        try:
            # Set default order to 'id' for contacts
            if 'order' not in additional_params:
                additional_params['order'] = 'id'

            additional_params.setdefault('optional_properties', 'lead_source_id,custom_fields,job_title')
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            response = self.get('contacts', params)
            
            # Log API response details
            logger.info(f"API response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            logger.info(f"API response type: {type(response)}")
            if isinstance(response, dict):
                if 'contacts' in response:
                    contacts_list = response.get('contacts', [])
                    logger.info(f"API returned {len(contacts_list)} contacts in response")
                    if contacts_list:
                        logger.info(f"Sample contact keys: {list(contacts_list[0].keys()) if isinstance(contacts_list[0], dict) else type(contacts_list[0])}")
                        logger.info(f"Sample contact ID: {contacts_list[0].get('id') if isinstance(contacts_list[0], dict) else 'N/A'}")
                else:
                    logger.warning(f"Response missing 'contacts' key. Available keys: {list(response.keys())}")
            logger.debug(f"Full API response: {response}")

            if not response or 'contacts' not in response:
                logger.warning(f"Invalid response format from contacts API: {response}")
                return [], {'next': None, 'count': 0, 'total': 0}

            # Transform each contact with its related data
            items = []
            for item in response.get('contacts', []):
                try:
                    if not item:
                        logger.warning(f"Skipping empty contact item")
                        continue
                    transformed_contact = transform_contact_with_related(item, db_session)
                    if transformed_contact is None:
                        logger.warning(f"Transformation returned None for contact: {item.get('id', 'unknown')}")
                        continue
                    if not hasattr(transformed_contact, 'id') or transformed_contact.id is None:
                        logger.warning(f"Transformed contact missing ID: {item.get('id', 'unknown')}")
                        continue
                    items.append(transformed_contact)
                except Exception as e:
                    logger.error(f"Error transforming contact {item.get('id', 'unknown')}: {str(e)}", exc_info=True)
                    logger.debug(f"Problematic contact data: {item}")
                    continue

            # Extract pagination metadata
            pagination = {'next': response.get('next'), 'count': response.get('count'), 'total': response.get('total')}

            logger.info(f"Successfully retrieved {len(items)} contacts")
            return items, pagination

        except Exception as e:
            logger.error(f"Error fetching contacts: {str(e)}")
            raise

    def get_contact(self, contact_id: int):
        """Get a single contact by ID with all related data."""
        params = {'optional_properties': 'lead_source_id,custom_fields,job_title'}
        response = self.get(f'contacts/{contact_id}', params)
        logger.debug(f"Raw contact API response: {response}")
        return transform_contact_with_related(response)

    def get_contact_model(self) -> Dict[str, Any]:
        """Get the contact model definition from the API.
        
        Returns:
            Dictionary containing the contact model definition
        """
        response = self.get('contacts/model')
        return response

    def get_contact_tags(self, contact_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of tags applied to a specific contact."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'contacts/{contact_id}/tags', params)
        items = [transform_applied_tag(tag_data) for tag_data in response.get('tags', [])]
        pagination = {'next': None, 'count': len(items), 'total': len(items)}
        return items, pagination

    def get_contact_credit_cards(self, contact_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Get credit cards for a specific contact."""
        try:
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            endpoint = f"contacts/{contact_id}/creditCards"
            response = self._make_request('GET', endpoint, params=params)

            if isinstance(response, list):
                items = response
            elif isinstance(response, dict):
                items = response.get('creditCards', [])
            else:
                logger.warning(f"Unexpected response format for credit cards: {response}")
                items = []

            transformed_items = []
            for item in items:
                try:
                    if isinstance(item, dict):
                        item['contact_id'] = contact_id
                        transformed_items.append(item)
                except Exception as e:
                    logger.error(f"Error transforming credit card item: {str(e)}")
                    continue

            pagination = {'next': None, 'count': len(transformed_items), 'total': len(transformed_items)}
            return transformed_items, pagination

        except Exception as e:
            logger.error(f"Error fetching credit cards for contact {contact_id}: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    # Custom Fields Methods
    def get_custom_fields(self, entity_type: str = 'contacts', **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get all custom fields from the specified entity model."""
        valid_entity_types = ['contacts', 'companies', 'opportunities', 'orders', 'subscriptions']
        if entity_type not in valid_entity_types:
            raise ValueError(f"Invalid entity_type. Must be one of: {', '.join(valid_entity_types)}")

        model = self.get(f'{entity_type}/model')
        
        # Log API response details
        logger.info(f"Model API response keys: {list(model.keys()) if isinstance(model, dict) else 'Not a dict'}")
        logger.info(f"Model API response type: {type(model)}")
        if isinstance(model, dict):
            custom_fields_data = model.get('custom_fields', [])
            logger.info(f"Custom fields data type: {type(custom_fields_data)}")
            if isinstance(custom_fields_data, list):
                logger.info(f"Custom fields list length: {len(custom_fields_data)}")
                if custom_fields_data:
                    logger.info(f"Sample custom field: {custom_fields_data[0]}")
            elif isinstance(custom_fields_data, dict):
                logger.info(f"Custom fields dict keys: {list(custom_fields_data.keys())}")
                if custom_fields_data:
                    sample_key = list(custom_fields_data.keys())[0]
                    logger.info(f"Sample custom field key: {sample_key}, value: {custom_fields_data[sample_key]}")
        else:
            custom_fields_data = []
        
        custom_fields = []

        if isinstance(custom_fields_data, list):
            for field_def in custom_fields_data:
                try:
                    if not field_def:
                        logger.debug(f"Skipping empty field definition in {entity_type}")
                        continue
                    if not isinstance(field_def, dict):
                        logger.warning(f"Unexpected field_def type in {entity_type}: {type(field_def)}")
                        continue
                    if 'id' not in field_def:
                        logger.warning(f"Custom field missing 'id' in {entity_type}: {field_def}")
                        continue
                    field_name = field_def.get('field_name') or field_def.get('label', f"Field_{field_def.get('id')}")
                    custom_field = transform_custom_field(field_name, field_def)
                    if custom_field is None:
                        logger.warning(f"Transformation returned None for custom field in {entity_type}: {field_name}")
                        continue
                    if not hasattr(custom_field, 'id') or custom_field.id is None:
                        logger.warning(f"Custom field missing ID in {entity_type}: {field_name} (field_def: {field_def})")
                        continue
                    custom_fields.append(custom_field)
                except Exception as e:
                    logger.error(f"Error transforming custom field for {entity_type}: {str(e)}", exc_info=True)
                    continue
        elif isinstance(custom_fields_data, dict):
            for field_name, field_def in custom_fields_data.items():
                try:
                    if not field_def:
                        logger.debug(f"Skipping empty field definition in {entity_type}: {field_name}")
                        continue
                    if not isinstance(field_def, dict):
                        logger.warning(f"Unexpected field_def type in {entity_type} for {field_name}: {type(field_def)}")
                        continue
                    if 'id' not in field_def:
                        logger.warning(f"Custom field missing 'id' in {entity_type}: {field_name} (field_def: {field_def})")
                        continue
                    custom_field = transform_custom_field(field_name, field_def)
                    if custom_field is None:
                        logger.warning(f"Transformation returned None for custom field in {entity_type}: {field_name}")
                        continue
                    if not hasattr(custom_field, 'id') or custom_field.id is None:
                        logger.warning(f"Custom field missing ID in {entity_type}: {field_name}")
                        continue
                    custom_fields.append(custom_field)
                except Exception as e:
                    logger.error(f"Error transforming custom field {field_name} for {entity_type}: {str(e)}", exc_info=True)
                    continue
        else:
            logger.warning(f"Unexpected custom_fields format for {entity_type}: {type(custom_fields_data)}")

        pagination = {'next': None, 'count': len(custom_fields), 'total': len(custom_fields)}
        logger.info(f"Retrieved {len(custom_fields)} custom fields from {entity_type} model")
        return custom_fields, pagination

    def get_all_custom_fields(self, **additional_params) -> Dict[str, List]:
        """Get all custom fields from all entity models."""
        all_custom_fields = {}
        entity_types = ['contacts', 'companies', 'opportunities', 'orders', 'subscriptions']

        for entity_type in entity_types:
            try:
                custom_fields, _ = self.get_custom_fields(entity_type, **additional_params)
                all_custom_fields[entity_type] = custom_fields
            except Exception as e:
                logger.error(f"Error retrieving custom fields for {entity_type}: {str(e)}")
                all_custom_fields[entity_type] = []
                continue

        return all_custom_fields

    # Opportunity Related Methods
    def get_opportunities(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of opportunities."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
        response = self.get('opportunities', params)
        return transform_list_response(response, transform_opportunity)

    def get_opportunity(self, opportunity_id: int):
        """Get a single opportunity by ID."""
        try:
            response = self.get(f'opportunities/{opportunity_id}')
            return transform_opportunity(response)
        except Exception as e:
            logger.error(f"Error fetching opportunity {opportunity_id}: {str(e)}")
            raise

    # Product Related Methods
    def get_products(self, limit: int = 50, offset: int = 0, subscription_only: Optional[bool] = None, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of products."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, subscription_only=subscription_only, **additional_params)
        response = self.get('products', params)
        return transform_list_response(response, transform_product)

    def get_product(self, product_id: int):
        """Get a single product by ID."""
        response = self.get(f'products/{product_id}')
        return transform_product(response)

    # Order Related Methods
    def get_orders(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of orders."""
        if 'order' not in additional_params:
            additional_params['order'] = 'date_created'

        params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
        response = self.get('orders', params)
        return transform_list_response(response, transform_order_with_items)

    def get_order(self, order_id: int):
        """Get a single order by ID with its items."""
        response = self.get(f'orders/{order_id}')
        return transform_order_with_items(response)

    def get_order_items(self, order_id: int) -> List:
        """Get items for an order."""
        try:
            response = self.get(f'orders/{order_id}/items')
            return transform_list_response(response, transform_order_item)
        except KeapNotFoundError:
            logger.warning(f"No items found for order {order_id}")
            return []

    def get_order_payments(self, order_id: int) -> List:
        """Get payments for a specific order."""
        try:
            response = self._make_request('GET', f'orders/{order_id}/payments')
            if not response:
                logger.warning(f"No payments found for order {order_id}")
                return []
            
            if isinstance(response, list):
                payments = response
            elif isinstance(response, dict):
                payments = response.get('payments', [])
                if not payments:
                    payments = response.get('data', [])
                    if not payments:
                        logger.debug(f"No payments found in response for order {order_id}: {response}")
                        return []
            else:
                logger.warning(f"Unexpected response format for order payments {order_id}: {type(response)}")
                return []
            
            return [transform_order_payment(payment) for payment in payments]
        except Exception as e:
            logger.error(f"Error getting payments for order {order_id}: {str(e)}")
            return []

    def get_order_transactions(self, order_id: int) -> List:
        """Get transactions for a specific order."""
        try:
            response = self._make_request('GET', f'orders/{order_id}/transactions')
            if not response:
                logger.warning(f"No transactions found for order {order_id}")
                return []
            
            if isinstance(response, list):
                transactions = response
            elif isinstance(response, dict):
                transactions = response.get('transactions', [])
                if not transactions:
                    transactions = response.get('data', [])
                    if not transactions:
                        logger.debug(f"No transactions found in response for order {order_id}: {response}")
                        return []
            else:
                logger.warning(f"Unexpected response format for order transactions {order_id}: {type(response)}")
                return []
            
            return [transform_order_transaction(transaction) for transaction in transactions]
        except Exception as e:
            logger.error(f"Error getting transactions for order {order_id}: {str(e)}")
            return []

    def get_order_payment_plan(self, order_id: int) -> Any:
        """Get payment plan for a specific order."""
        try:
            response = self._make_request('GET', f'orders/{order_id}/paymentPlan')
            if not response:
                logger.debug(f"No payment plan found for order {order_id}")
                return None
            return transform_payment_plan(response, order_id)
        except Exception as e:
            logger.warning(f"Error getting payment plan for order {order_id}: {str(e)}")
            return None

    def get_payment_gateways(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[Any], Dict[str, Any]]:
        """Get a list of payment gateways."""
        try:
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            response = self.get('paymentGateways', params)
            items = [transform_payment_gateway(gateway) for gateway in response.get('paymentGateways', [])] if isinstance(response, dict) else [transform_payment_gateway(gateway) for gateway in response]
            pagination = {'next': response.get('next') if isinstance(response, dict) else None, 'count': len(items), 'total': len(items)}
            return items, pagination
        except Exception as e:
            logger.error(f"Error fetching payment gateways: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    # Task Related Methods
    def get_tasks(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of tasks."""
        try:
            if 'order' not in additional_params:
                additional_params['order'] = 'due_date'

            params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
            response = self.get('tasks', params)
            return transform_list_response(response, transform_task)
        except Exception as e:
            logger.error(f"Error fetching tasks: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    def get_task(self, task_id: int):
        """Get a single task by ID."""
        try:
            response = self.get(f'tasks/{task_id}')
            return transform_task(response)
        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {str(e)}")
            raise

    # Note Related Methods
    def get_notes(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of notes."""
        try:
            if 'order' not in additional_params:
                additional_params['order'] = 'date_created'

            params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
            response = self.get('notes', params)
            return transform_list_response(response, transform_note)
        except Exception as e:
            logger.error(f"Error fetching notes: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    def get_note(self, note_id: int):
        """Get a single note by ID."""
        try:
            response = self.get(f'notes/{note_id}')
            return transform_note(response)
        except Exception as e:
            logger.error(f"Error fetching note {note_id}: {str(e)}")
            raise

    # Campaign Related Methods
    def get_campaigns(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of campaigns."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get('campaigns', params)
        return transform_list_response(response, transform_campaign)

    def get_campaign(self, campaign_id: int):
        """Get a single campaign by ID."""
        response = self.get(f'campaigns/{campaign_id}')
        return transform_campaign(response)

    # Subscription Related Methods
    def get_subscriptions(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of subscriptions."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
        response = self.get('subscriptions', params)
        return transform_list_response(response, transform_subscription)

    # Account Related Methods
    def get_account_profile(self):
        """Get the account profile."""
        response = self.get('account/profile')
        return transform_account_profile(response)

    # Affiliate Related Methods
    def get_affiliates(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of affiliates."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get('affiliates', params)
        return transform_list_response(response, transform_affiliate)

    def get_affiliate(self, affiliate_id: int):
        """Get a single affiliate by ID."""
        response = self.get(f'affiliates/{affiliate_id}')
        return transform_affiliate(response)

    def get_affiliate_commissions(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get commissions for an affiliate."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/commissions', params)
        return transform_list_response(response, transform_affiliate_commission)

    def get_affiliate_programs(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get programs for an affiliate."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/programs', params)
        return transform_list_response(response, transform_affiliate_program)

    def get_affiliate_redirects(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get redirects for an affiliate."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/redirects', params)
        return transform_list_response(response, transform_affiliate_redirect)

    def get_affiliate_summary(self, affiliate_id: int):
        """Get summary for an affiliate."""
        response = self.get(f'affiliates/{affiliate_id}/summary')
        return transform_affiliate_summary(response)

    def get_affiliate_clawbacks(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get clawbacks for an affiliate."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/clawbacks', params)
        return transform_list_response(response, transform_affiliate_clawback)

    def get_affiliate_payments(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get payments for an affiliate."""
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/payments', params)
        return transform_list_response(response, transform_affiliate_payment)

    # Tag Related Methods
    def get_tags(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List, Dict[str, Any]]:
        """Get a list of tags."""
        try:
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            response = self.get('tags', params)
            logger.debug(f"Raw tags API response: {response}")

            if not response:
                logger.warning("Empty response received from tags API")
                return [], {'next': None, 'previous': None, 'count': 0, 'limit': limit, 'offset': offset}

            return transform_list_response(response, transform_tag)

        except Exception as e:
            logger.error(f"Error fetching tags: {str(e)}")
            return [], {'next': None, 'previous': None, 'count': 0, 'limit': limit, 'offset': offset}

    def get_tag(self, tag_id: int):
        """Get a single tag by ID."""
        try:
            response = self.get(f'tags/{tag_id}')
            logger.debug(f"Raw tag API response: {response}")
            return transform_tag(response)
        except Exception as e:
            logger.error(f"Error fetching tag {tag_id}: {str(e)}")
            raise

