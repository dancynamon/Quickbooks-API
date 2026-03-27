"""QuickBooks Online Payment operations."""

from quickbooks_api.entities.base import BaseService


class PaymentService(BaseService):
    entity_name = "Payment"
    entity_url = "/payment"

    def create_payment(
        self,
        customer_id: str | int,
        total_amount: float,
        invoice_ids: list[str | int] | None = None,
        payment_method_ref: str | None = None,
        deposit_to_account_id: str | None = None,
    ) -> dict:
        """Create a payment, optionally linked to invoices."""
        data: dict = {
            "CustomerRef": {"value": str(customer_id)},
            "TotalAmt": total_amount,
        }

        if invoice_ids:
            data["Line"] = [
                {
                    "Amount": total_amount / len(invoice_ids),
                    "LinkedTxn": [{"TxnId": str(inv_id), "TxnType": "Invoice"}],
                }
                for inv_id in invoice_ids
            ]

        if payment_method_ref:
            data["PaymentMethodRef"] = {"value": payment_method_ref}
        if deposit_to_account_id:
            data["DepositToAccountRef"] = {"value": deposit_to_account_id}

        return self.create(data)

    def find_by_customer(self, customer_id: str | int) -> list[dict]:
        """Find all payments for a customer."""
        return self.query(where=f"CustomerRef = '{customer_id}'")

    def void_payment(self, payment_id: str | int, sync_token: str) -> dict:
        """Void a payment."""
        data = {"Id": str(payment_id), "SyncToken": sync_token}
        resp = self.client._request(
            "POST", self.entity_url, json_data=data, params={"operation": "void"}
        )
        return resp.get(self.entity_name, resp)
