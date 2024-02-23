from ticket import Ticket
from discount_policy import BaseDiscountPolicy

class FareCalculator:
    BASE_FARE_PER_MILE = 0.5  # Example base fare

    def __init__(self, discount_policy=None):
        if discount_policy is None:
            discount_policy = BaseDiscountPolicy()
        self.discount_policy = discount_policy

    def calculate_fare(self, ticket: Ticket):
        base_fare = ticket.journey.distance * self.BASE_FARE_PER_MILE
        discount = self.discount_policy.apply_discount(ticket, base_fare)
        return max(base_fare - discount, 0)  # Fare should not be negative