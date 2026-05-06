"""Unit tests for the bot application entrypoint."""

from unittest.mock import MagicMock, patch

from pyball.infrastructure.telegram.bot.entrypoint import create_application


class TestCreateApplication:
    """Tests for create_application."""

    @patch("pyball.infrastructure.telegram.bot.entrypoint.Application")
    def test_uses_injected_settings_bot_token(self, mock_application_class):
        """create_application forwards the injected settings' bot token to the builder."""
        settings = MagicMock()
        settings.telegram.bot_token = "test-token-123"

        mock_builder = MagicMock()
        mock_application_class.builder.return_value = mock_builder
        mock_builder.token.return_value = mock_builder
        mock_builder.concurrent_updates.return_value = mock_builder
        mock_app = MagicMock()
        mock_builder.build.return_value = mock_app

        create_application(settings)

        mock_builder.token.assert_called_once_with("test-token-123")
        mock_app.add_handler.assert_called_once()
