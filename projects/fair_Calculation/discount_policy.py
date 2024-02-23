from ticket import Ticket

class BaseDiscountPolicy:
    def apply_discount(self, ticket: Ticket, base_fare: float) -> float:
        # Example base discount policy, no discount
        return 0.0