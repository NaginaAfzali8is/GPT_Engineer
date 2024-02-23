from dataclasses import dataclass
from journey import Journey
from passenger import Passenger

@dataclass
class Ticket:
    journey: Journey
    passenger: Passenger