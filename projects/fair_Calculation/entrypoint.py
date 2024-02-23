from fare_calculator import FareCalculator
from journey import Journey
from passenger import Passenger
from ticket import Ticket

def main():
    # Example usage
    journey = Journey(origin="New York", destination="Washington D.C.", distance=225)
    passenger = Passenger(age=25)
    ticket = Ticket(journey=journey, passenger=passenger)

    calculator = FareCalculator()
    fare = calculator.calculate_fare(ticket)
    print(f"The fare for your journey is: ${fare:.2f}")

if __name__ == "__main__":
    main()