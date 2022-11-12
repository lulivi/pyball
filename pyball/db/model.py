# Copyright (c) 2022 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Database models."""

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    CompositeKey,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    Proxy,
)

database = Proxy()


class BaseModel(Model):
    """Base table model."""

    class Meta:
        """Meta for all the child models."""

        database = database
        # Convert PascalCase to snake_case
        table_function = lambda model_class: "".join(
            [f"_{i.lower()}" if i.isupper() else i for i in model_class.__name__]
        ).lstrip("_")


class Player(BaseModel):
    """Player statistics and information."""

    id = IntegerField(primary_key=True)
    name = CharField(null=False, unique=True)
    main = BooleanField(null=False)
    goals = IntegerField(default=0)
    assists = IntegerField(default=0)
    wins = IntegerField(default=0)
    losses = IntegerField(default=0)
    ties = IntegerField(default=0)
    rank = IntegerField(default=0)
    skill = FloatField(default=0.0)


class MatchStatistic(BaseModel):
    """Statiscics of players in matches."""

    date = DateTimeField(null=False)
    player = ForeignKeyField(Player)
    team = CharField(null=False)
    goals = IntegerField(default=0)
    assists = IntegerField(default=0)

    class Meta:
        primary_key = CompositeKey("date", "player")
