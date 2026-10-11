# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


class FlightInsurance(gl.Contract):
    # User -> flight_key -> premium paid
    policies: TreeMap[Address, TreeMap[str, u256]]

    # User -> flight_key -> status (stored as u256, same type as `policies`)
    #
    # 0 = Active
    # 1 = PaidOut
    # 2 = Rejected
    # 3 = DataUnavailable
    policy_status: TreeMap[Address, TreeMap[str, u256]]

    # Fixed premium and payout
    PREMIUM_COST = u256(10**16)
    PAYOUT_AMOUNT = u256(5 * 10**16)

    def __init__(self):
        pass

    @gl.public.write.payable
    def buy_policy(self, flight_key: str) -> None:
        """Buy insurance for a specific flight."""

        if gl.message.value < self.PREMIUM_COST:
            raise gl.vm.UserError("Insufficient premium paid.")

        user = gl.message.sender_address

        if user not in self.policies:
            self.policies[user] = TreeMap[str, u256]()

        if user not in self.policy_status:
            self.policy_status[user] = TreeMap[str, u256]()

        if flight_key in self.policies[user]:
            raise gl.vm.UserError(
                "Policy already active for this flight."
            )

        self.policies[user][flight_key] = gl.message.value
        self.policy_status[user][flight_key] = u256(0)

    @gl.public.write
    def claim_payout(
        self,
        flight_key: str,
        airline_code: str,
        flight_number: str,
        departure_date: str,
    ) -> str:
        """
        Check external flight information and determine whether
        the policy qualifies for a payout.

        0 = Active
        1 = PaidOut
        2 = Rejected
        3 = DataUnavailable
        """

        user = gl.message.sender_address

        if user not in self.policies:
            raise gl.vm.UserError(
                "No active insurance policy found."
            )

        if flight_key not in self.policies[user]:
            raise gl.vm.UserError(
                "No active insurance policy found for this flight."
            )

        if self.policy_status[user][flight_key] != u256(0):
            raise gl.vm.UserError(
                "This claim has already been processed."
            )

        # Secure flight-data proxy.
        #
        # The Aviationstack API key stays on Vercel and is never
        # exposed inside this Intelligent Contract.
        url = (
            "https://flight-proxy-bice.vercel.app/api/flight-status"
            f"?airline={airline_code}"
            f"&flight={flight_number}"
            f"&date={departure_date}"
        )

        def check_flight():
            import json

            response = gl.nondet.web.get(url)

            if response.status != 200:
                return "DATA_UNAVAILABLE"

            if response.body is None:
                return "DATA_UNAVAILABLE"

            try:
                payload = json.loads(response.body.decode("utf-8"))
            except Exception:
                return "DATA_UNAVAILABLE"

            if not isinstance(payload, dict):
                return "DATA_UNAVAILABLE"

            if payload.get("status") != "AVAILABLE":
                return "DATA_UNAVAILABLE"

            records = payload.get("data")

            if not isinstance(records, list) or len(records) == 0:
                return "DATA_UNAVAILABLE"

            record = records[0]

            if not isinstance(record, dict):
                return "DATA_UNAVAILABLE"

            flight_state = record.get("flight_status")

            # A cancelled flight qualifies for a payout.
            if flight_state == "cancelled":
                return "DELAYED"

            # Anything other than landed has no final arrival delay yet.
            if flight_state != "landed":
                return "DATA_UNAVAILABLE"

            arrival = record.get("arrival")

            if not isinstance(arrival, dict):
                return "DATA_UNAVAILABLE"

            delay = arrival.get("delay")

            # Never infer a missing delay. bool is excluded because
            # it is a subclass of int in Python.
            if isinstance(delay, bool) or not isinstance(delay, (int, float)):
                return "DATA_UNAVAILABLE"

            if delay > 120:
                return "DELAYED"

            return "ONTIME"

        # Every validator runs the same deterministic check and the
        # results are compared by exact equality (no LLM involved).
        decision = gl.eq_principle.strict_eq(check_flight)

        # Deterministic state changes happen only after the
        # consensus-agreed result has been returned.
        if decision == "DELAYED":
            # Make sure the contract can actually pay. Raising here
            # reverts the whole transaction, so the claim stays
            # Active and can be retried once the contract has funds.
            if self.balance < self.PAYOUT_AMOUNT:
                raise gl.vm.UserError(
                    "Insufficient contract balance for payout."
                )

            # Update state BEFORE sending funds so the same claim
            # can never be paid twice.
            self.policy_status[user][flight_key] = u256(1)

            # EVM-style transfer: this is the route that credits an
            # externally owned account (a plain get_contract_at(...)
            # transfer was debited from the contract but never credited).
            _Recipient(user).emit_transfer(
                value=self.PAYOUT_AMOUNT
            )

            return "CLAIM_APPROVED"

        if decision == "ONTIME":
            self.policy_status[user][flight_key] = u256(2)
            return "CLAIM_REJECTED"

        self.policy_status[user][flight_key] = u256(3)
        return "DATA_UNAVAILABLE"

    @gl.public.view
    def get_policy_state(
        self,
        user: str,
        flight_key: str,
    ) -> u8:
        """Return the current status of a flight policy."""

        account = Address(user)

        if account not in self.policy_status:
            return u8(0)

        if flight_key not in self.policy_status[account]:
            return u8(0)

        return u8(int(self.policy_status[account][flight_key]))