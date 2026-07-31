# ═══════════════════════════════════════════════════════════════════════
# RPA Smart Attendance System — Notification Utilities
# SMS functionality has been deprecated in v2.0.
# Email is now the sole notification channel.
# This file is kept as a stub to prevent import errors.
# ═══════════════════════════════════════════════════════════════════════

import logging

logger = logging.getLogger(__name__)


def send_sms(phone, message):
    """
    DEPRECATED — SMS notifications have been removed in v2.0.
    This stub is retained so any lingering import references do not crash.
    Returns a dict that mirrors the old signature.
    """
    logger.info("[SMS-DEPRECATED] SMS sending is disabled. Email notifications are used instead.")
    return {'success': False, 'error': 'SMS has been deprecated in RPA Smart Attendance System v2.0'}


# Backward-compatibility alias
send_fast2sms_sms = send_sms
