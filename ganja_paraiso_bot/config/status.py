"""
Order status definitions for the Ganja Paraiso bot.
"""
from ganja_paraiso_bot.config.emoji import EMOJI

# Status definitions
STATUS = {
    "pending_payment": {
        "label": "Pending Payment Review",
        "description": "We're currently reviewing your payment. This usually takes 1-2 hours during business hours.",
        "emoji": EMOJI["warning"]
    },
    "payment_confirmed": {
        "label": "Payment Confirmed and Preparing Order",
        "description": "Great news! Your payment has been confirmed and we're now preparing your order. We'll update you again when it's ready for delivery.",
        "emoji": EMOJI["success"]
    },
    "booking": {
        "label": "Booking",
        "description": "We're currently booking a delivery partner for your order. This process typically takes 1-3 hours depending on availability.",
        "emoji": EMOJI["info"]
    },
    "booked": {
        "label": "Booked",
        "description": "Good news! Your order has been booked with a delivery partner and is on its way.",
        "emoji": EMOJI["deliver"],
        "with_tracking": "Good news! Your order has been booked with Lalamove and is on its way. You can track your delivery in real-time using the link below:"
    },
    "delivered": {
        "label": "Delivered",
        "description": "Your order has been delivered! We hope you enjoy your products. Thank you for choosing Ganja Paraiso!",
        "emoji": EMOJI["success"]
    },
    "payment_rejected": {
        "label": "Payment Rejected",
        "description": "Unfortunately, there was an issue with your payment. Please contact customer support for assistance.",
        "emoji": EMOJI["error"]
    }
}