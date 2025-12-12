"""
Centralized datetime management utilities for ChronoScope.

Provides robust date/datetime parsing and normalization for timeline events.
"""

from datetime import datetime, date, time
from typing import Union, Optional


class DateTimeManager:
    """Centralized datetime management for timeline applications with robust parsing."""

    @staticmethod
    def normalize_to_date(date_input: Union[datetime, date, str, None]) -> Optional[date]:
        """
        Convert any date-like input to a date object.

        Args:
            date_input: Input to convert - datetime, date, string, or None

        Returns:
            Normalized date object or None if conversion fails

        Raises:
            TypeError: If input type is not supported
        """
        if date_input is None:
            return None

        if isinstance(date_input, datetime):
            return date_input.date()

        if isinstance(date_input, date):
            return date_input

        if isinstance(date_input, str):
            try:
                # Try parsing ISO 8601 format with fromisoformat first (handles microseconds)
                try:
                    return datetime.fromisoformat(date_input).date()
                except (ValueError, AttributeError):
                    pass

                # Try parsing common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        parsed = datetime.strptime(date_input, fmt)
                        return parsed.date()
                    except ValueError:
                        continue
                raise ValueError(f"Unable to parse date string: {date_input}")
            except ValueError as e:
                print(f"Warning: {e}")
                return None

        raise TypeError(f"Unsupported date type: {type(date_input)}")

    @staticmethod
    def normalize_to_datetime(date_input: Union[datetime, date, str, None],
                            default_time: time = time.min) -> Optional[datetime]:
        """
        Convert any date-like input to a datetime object.

        Args:
            date_input: Input to convert - datetime, date, string, or None
            default_time: Time to use when converting from date (default: midnight)

        Returns:
            Normalized datetime object or None if conversion fails

        Raises:
            TypeError: If input type is not supported
        """
        if date_input is None:
            return None

        if isinstance(date_input, datetime):
            return date_input

        if isinstance(date_input, date):
            return datetime.combine(date_input, default_time)

        if isinstance(date_input, str):
            try:
                # Try parsing ISO 8601 format with fromisoformat first (handles microseconds)
                try:
                    return datetime.fromisoformat(date_input)
                except (ValueError, AttributeError):
                    pass

                # Try parsing common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(date_input, fmt)
                    except ValueError:
                        continue

                # If no time component, parse as date and add default time
                date_part = DateTimeManager.normalize_to_date(date_input)
                if date_part:
                    return datetime.combine(date_part, default_time)

                raise ValueError(f"Unable to parse datetime string: {date_input}")
            except ValueError as e:
                print(f"Warning: {e}")
                return None

        raise TypeError(f"Unsupported datetime type: {type(date_input)}")