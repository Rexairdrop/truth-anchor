# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


class FlightInsurance(gl.Contract):
    # User -> flight_key -> premium paid
    policies: TreeMap[Address, TreeMap[str, u256]]

    # flight_key -> status
    # 0 = Active
    # 1 = PaidOut
    # 2 = Rejected
    # 3 = DataUnavailable
    flight_status: TreeMap[str, u8]

    # Fixed premium and payout
    PREMIUM_COST = u256(10**16)
    PAYOUT_AMOUNT = u256(5 * 10**16)

    @gl.public.write.payable
    def buy_policy(self, flight_key: str) -> None:
        """Buy insurance for a specific flight."""

        if gl.message.value < self.PREMIUM_COST:
            raise gl.vm.UserError("Insufficient premium paid.")

        user = gl.message.sender_address

        if user not in self.policies:
            self.policies[user] = TreeMap[str, u256]()

        if flight_key in self.policies[user]:
            raise gl.vm.UserError(
                "Policy already active for this flight."
            )

        self.policies[user][flight_key] = gl.message.value
        self.flight_status[flight_key] = u8(0)

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

        if self.flight_status.get(flight_key, u8(0)) != u8(0):
            raise gl.vm.UserError(
                "This claim has already been processed."
            )

        # This URL should point to your secure flight-data proxy.
        #
        # IMPORTANT:
        # Do not put your Aviationstack secret directly into this
        # Intelligent Contract.
        #
        # Your proxy should accept these query parameters and return
        # the relevant Aviationstack flight data.
        url = (
            "https://YOUR-FLIGHT-PROXY-DOMAIN.vercel.app/api/flight-status"
            f"?airline={airline_code}"
            f"&flight={flight_number}"
            f"&date={departure_date}"
        )

        def check_flight():
            response = gl.nondet.web.get(url)

            # HTTP-level failure
            if response.status_code != 200:
                return "DATA_UNAVAILABLE"

            body = response.body.decode("utf-8")

            # Empty response
            if not body:
                return "DATA_UNAVAILABLE"

            prompt = f"""
You are evaluating a flight-insurance claim.

Flight:
Airline IATA: {airline_code}
Flight number: {flight_number}
Departure date: {departure_date}

The flight-data source returned:

{body}

Determine the insurance outcome using ONLY the information
contained in the supplied flight-data response.

Rules:

1. Return DELAYED if the flight was cancelled.

2. Return DELAYED if the flight arrived more than 120 minutes
   after its scheduled arrival time.

3. Return ONTIME if the flight was not cancelled and arrived
   no more than 120 minutes late.

4. Return DATA_UNAVAILABLE if:
   - the response contains no matching flight,
   - the response reports an API/data error,
   - the flight data is missing,
   - the relevant arrival information is unavailable,
   - or the supplied information is insufficient to make the decision.

Return ONLY one of:

DELAYED
ONTIME
DATA_UNAVAILABLE
"""

            result = gl.nondet.exec_prompt(prompt)
            result = result.strip().upper()

            if result == "DELAYED":
                return "DELAYED"

            if result == "ONTIME":
                return "ONTIME"

            return "DATA_UNAVAILABLE"

        decision = gl.eq_principle.prompt_comparative(
            check_flight,
            """
Validators should agree on the substantive insurance outcome.

The only valid outcomes are:

DELAYED
ONTIME
DATA_UNAVAILABLE

The outcome must be based on the supplied flight data.

DATA_UNAVAILABLE must be used when the source does not provide
enough reliable information to determine whether the flight
qualifies for payout.

Do not treat missing, empty, invalid, or API-error responses
as ONTIME.
""",
        )

        if decision == "DELAYED":
            self.flight_status[flight_key] = u8(1)
            return "CLAIM_APPROVED"

        if decision == "ONTIME":
            self.flight_status[flight_key] = u8(2)
            return "CLAIM_REJECTED"

        self.flight_status[flight_key] = u8(3)
        return "DATA_UNAVAILABLE"

    @gl.public.view
    def get_policy_state(
        self,
        user: str,
        flight_key: str,
    ) -> u8:
        """Return the current status of a flight policy."""

        account = Address(user)

        if account not in self.policies:
            return u8(0)

        if flight_key not in self.policies[account]:
            return u8(0)

        if flight_key not in self.flight_status:
            return u8(0)

        return self.flight_status[flight_key]