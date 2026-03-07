
from agent.tickets.tool_tickets import (
    TICKET_SLOTS,
    get_next_missing_slot,
    fill_slot,
    create_ticket,
)

class TicketHandler:
    """
    Stateful handler for the CREATE_TICKET intent.

    Usage:
        handler = TicketHandler()

        # Each turn: pass in the user's latest message
        response = handler.handle("My package arrived damaged")

        # When handler.is_done() → True, the ticket has been submitted
    """

    def __init__(self):
        self.collected: dict = {}        # slots filled so far
        self.current_slot: dict = None   # slot we're currently asking about
        self.done: bool = False
        self.result: dict = None         # final API response
        self.attempts: dict = {}         # track retries per slot

    def is_done(self) -> bool:
        return self.done

    def handle(self, user_message: str) -> str:
        """
        Process one user turn. Returns the agent's next response.
        """
        user_message = user_message.strip()

        # If we're waiting for a value for the current slot, process it
        if self.current_slot:
            slot_key = self.current_slot["key"]

            # Handle user skipping an optional slot
            if user_message.lower() in ("skip", "no", "none", "-", "n/a") and not self.current_slot.get("required"):
                self.collected[slot_key] = None
                self.current_slot = None
                return self._next_turn()

            success, error = fill_slot(self.collected, slot_key, user_message)

            if not success:
                # Track retry attempts, todo: add custom number of retries per slot
                self.attempts[slot_key] = self.attempts.get(slot_key, 0) + 1
                if self.attempts[slot_key] >= 3:
                    # After 3 failed attempts on a required slot, escalate
                    if self.current_slot.get("required"):
                        self.done = True
                        # Add custom message for escalation after failed retries
                        return (
                            "I wasn't able to collect the required information after several attempts. "
                            "I'll escalate this to a human agent who can assist you directly."
                        )
                    # Non-required: skip it
                    self.collected[slot_key] = None
                    self.current_slot = None
                    return self._next_turn()

                return f"{error}\n\n{self.current_slot['question']}"

            # Slot filled successfully
            self.current_slot = None

        return self._next_turn()

    def _next_turn(self) -> str:
        """Determine what to do next: ask for a slot or submit."""
        next_slot = get_next_missing_slot(self.collected)

        if next_slot:
            self.current_slot = next_slot
            return next_slot["question"]

        # All required slots collected — submit the ticket
        return self._submit()

    def _submit(self) -> str:
        """Call the API and return a confirmation or error message."""
        response = create_ticket(self.collected)
        self.done = True
        self.result = response

        if response["success"]:
            ticket = response["data"]["ticket"]
            return (
                f"Your ticket has been created successfully.\n\n"
                f"Ticket ID: {ticket['ticket_id']}\n"
                f"Shipment: {ticket['shipment_id']}\n"
                f"Issue: {ticket['issue_type']}\n"
                f"Status: {ticket['status']}\n\n"
                f"Our team will review your case and reach out"
                + (f" at {ticket['contact_email']}." if ticket.get("contact_email") else " shortly.")
            )
        else:
            return (
                f"There was a problem creating your ticket: {response['error']}\n"
                "Please try again or contact support directly."
            )

    def summary(self) -> dict:
        """Return a summary of collected slots (for logging/debugging)."""
        return {
            "collected_slots": self.collected,
            "done": self.done,
            "result": self.result,
        }

