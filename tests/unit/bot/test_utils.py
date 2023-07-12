from unittest import TestCase

import faker

from pyball.bot.utils import md_monospace_items

fake: faker.Faker = faker.Faker()


class TestMarkdownListFormating(TestCase):
    def test_markdown_monospace_item_list_creation(self):
        item_a = fake.name()
        item_b = fake.name()
        item_c = fake.name()
        input_list = [item_a, item_b, item_c]
        expected_output = f"`{item_a}`, `{item_b}`, `{item_c}`"
        output = md_monospace_items(input_list)

        self.assertEqual(output, expected_output)

    def test_markdown_monospace_item_list_when_no_elements(self):
        input_list = []
        expected_output = ""
        output = md_monospace_items(input_list)

        self.assertEqual(output, expected_output)
