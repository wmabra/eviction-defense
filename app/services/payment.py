"""Authorize.net payment service — sandbox & live."""
import os
from dataclasses import dataclass
from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from app.config import settings


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str | None = None
    message: str = ""
    auth_code: str | None = None


def get_merchant_auth():
    """Get Authorize.net merchant authentication object."""
    login = settings.authorize_login_id or os.getenv("AUTHORIZE_LOGIN_ID", "")
    key = settings.authorize_transaction_key or os.getenv("AUTHORIZE_TRANSACTION_KEY", "")
    
    merchant = apicontractsv1.merchantAuthenticationType()
    merchant.name = login
    merchant.transactionKey = key
    return merchant


def charge_card(opaque_data: dict, amount_cents: int, order_id: str, 
                customer_email: str, description: str = "Eviction Defense Packet") -> PaymentResult:
    """Charge a card using Authorize.net Accept.js opaque data.
    
    Args:
        opaque_data: The opaqueData from Accept.js (dataDescriptor + dataValue)
        amount_cents: Amount in cents ($395.00 = 39500)
        order_id: Unique order identifier
        customer_email: Customer's email for receipt
        description: Order description
    """
    if not settings.authorize_sandbox:
        # Live mode
        pass  # Same API, different endpoint configured in settings

    merchant = get_merchant_auth()
    
    # Set up the payment
    opaque = apicontractsv1.opaqueDataType()
    opaque.dataDescriptor = opaque_data.get("dataDescriptor", "")
    opaque.dataValue = opaque_data.get("dataValue", "")
    
    # Payment details
    payment = apicontractsv1.paymentType()
    payment.opaqueData = opaque
    
    # Order info
    order = apicontractsv1.orderType()
    order.invoiceNumber = order_id
    order.description = description
    
    # Customer info
    customer = apicontractsv1.customerDataType()
    customer.email = customer_email
    
    # Transaction request
    transaction = apicontractsv1.transactionRequestType()
    transaction.transactionType = "authCaptureTransaction"
    transaction.amount = amount_cents / 100  # Authorize.net uses decimal dollars
    transaction.payment = payment
    transaction.order = order
    transaction.customer = customer
    
    request = apicontractsv1.createTransactionRequest()
    request.merchantAuthentication = merchant
    request.refId = order_id
    request.transactionRequest = transaction
    
    controller = createTransactionController(request)
    controller.execute()
    
    response = controller.getresponse()
    
    if response is not None:
        if response.messages.resultCode == "Ok":
            txn = response.transactionResponse
            return PaymentResult(
                success=True,
                transaction_id=txn.transId,
                auth_code=txn.authCode if hasattr(txn, 'authCode') else None,
                message=txn.messages.message[0].text if txn.messages else "Payment successful"
            )
        else:
            errors = []
            if response.transactionResponse and response.transactionResponse.errors:
                for err in response.transactionResponse.errors.error:
                    errors.append(err.errorText)
            else:
                for msg in response.messages.message:
                    errors.append(msg.text)
            return PaymentResult(
                success=False,
                message="; ".join(errors)
            )
    
    return PaymentResult(success=False, message="No response from payment gateway")


def validate_card(opaque_data: dict) -> PaymentResult:
    """Validate a card without charging (Auth Only, $0.00)."""
    merchant = get_merchant_auth()
    
    opaque = apicontractsv1.opaqueDataType()
    opaque.dataDescriptor = opaque_data.get("dataDescriptor", "")
    opaque.dataValue = opaque_data.get("dataValue", "")
    
    payment = apicontractsv1.paymentType()
    payment.opaqueData = opaque
    
    transaction = apicontractsv1.transactionRequestType()
    transaction.transactionType = "authOnlyTransaction"
    transaction.amount = 0.00
    transaction.payment = payment
    
    request = apicontractsv1.createTransactionRequest()
    request.merchantAuthentication = merchant
    request.transactionRequest = transaction
    
    controller = createTransactionController(request)
    controller.execute()
    
    response = controller.getresponse()
    
    if response and response.messages.resultCode == "Ok":
        return PaymentResult(success=True, message="Card validated")
    
    return PaymentResult(success=False, message="Card validation failed")
