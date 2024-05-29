from peewee import Model, Proxy

database = Proxy()


class BaseModel(Model):
    """Base table model."""

    class Meta:
        """Set general table configuration."""

        database = database
