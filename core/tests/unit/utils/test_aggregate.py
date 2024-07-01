import uuid

from unittest import TestCase

import faker

from ddt import data, ddt

from pyball.utils.aggregate import Aggregate, Event

fake: faker.Faker = faker.Faker()


class FakeEventA(Event):
    def __init__(self, data):
        self.data = data

    @property
    def bus_string(self):
        return "FAKE_EVENT_A"


class FakeEventB(Event):
    def __init__(self, text, number):
        self.text = text
        self.number = number

    @property
    def bus_string(self):
        return "FAKE_EVENT_B"


class TestAggregate(TestCase):
    def test_it_should_consume_all_the_events(self) -> None:
        # Arrange
        aggregate = Aggregate()
        aggregate.trigger_event(FakeEventA("juan"))
        aggregate.trigger_event(FakeEventB("juan", 5))

        # Act
        events = list(aggregate.consume_events())

        # Assert
        self.assertEqual(len(events), 2)
        self.assertIsInstance(events[0], FakeEventA)
        self.assertIsInstance(events[1], FakeEventB)
