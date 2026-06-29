import logging
from typing import Optional

from sqlalchemy.orm import Session as SASession

from supportai.db.models import FAQEntry

logger = logging.getLogger(__name__)

SEED_FAQS = [
    {
        "question": "How do I reset my password?",
        "answer": "To reset your password, click on 'Forgot Password' on the login page. You will receive a password reset link via email. Follow the link to create a new password. Make sure your new password is at least 8 characters long and includes a mix of letters, numbers, and special characters.",
        "intent_tags": ["account"],
    },
    {
        "question": "How do I update my email address?",
        "answer": "To update your email address, go to Account Settings > Profile > Email. Enter your new email address and confirm it. A verification link will be sent to your new email. Click the link to complete the update.",
        "intent_tags": ["account"],
    },
    {
        "question": "How do I delete my account?",
        "answer": "To delete your account, go to Account Settings > Privacy > Delete Account. Please note that account deletion is permanent and all your data will be removed within 30 days. You will receive a confirmation email before the final deletion.",
        "intent_tags": ["account"],
    },
    {
        "question": "I forgot my username",
        "answer": "Your username is the email address you used during registration. If you have multiple accounts, check your email inbox for your registration confirmation email. Alternatively, contact our support team with your full name and we can help locate your account.",
        "intent_tags": ["account"],
    },
    {
        "question": "How do I enable two-factor authentication?",
        "answer": "To enable two-factor authentication (2FA), go to Account Settings > Security > Two-Factor Authentication. Download an authenticator app like Google Authenticator or Authy. Scan the QR code displayed on screen and enter the verification code to confirm setup.",
        "intent_tags": ["account"],
    },
    {
        "question": "I was charged twice for the same invoice",
        "answer": "I apologize for the duplicate charge. This is typically caused by a payment processing error. Please send us the invoice numbers of both charges via support ticket. We will investigate and issue a refund for the duplicate payment within 5-7 business days.",
        "intent_tags": ["billing"],
    },
    {
        "question": "How do I update my payment method?",
        "answer": "To update your payment method, go to Account Settings > Billing > Payment Methods. You can add a new credit card, link a PayPal account, or remove existing payment methods. The new method will be used for all future charges.",
        "intent_tags": ["billing"],
    },
    {
        "question": "Can I get a refund?",
        "answer": "Yes, we offer a 30-day money-back guarantee on all plans. To request a refund, go to Account Settings > Billing > Request Refund. Refunds are processed within 5-10 business days and will be credited to your original payment method.",
        "intent_tags": ["billing"],
    },
    {
        "question": "How does your pricing work?",
        "answer": "We offer three pricing tiers: Basic ($19/mo), Pro ($49/mo), and Enterprise (custom pricing). Each tier includes different feature sets and usage limits. You can view the full comparison on our Pricing page. All plans include a 14-day free trial with no credit card required.",
        "intent_tags": ["billing"],
    },
    {
        "question": "How do I upgrade my plan?",
        "answer": "To upgrade your plan, go to Account Settings > Billing > Plan Details. Select the plan you want to upgrade to. The price difference will be prorated for the remainder of your current billing cycle. The new features will be available immediately.",
        "intent_tags": ["billing"],
    },
    {
        "question": "How do I download an invoice?",
        "answer": "To download an invoice, go to Account Settings > Billing > Invoices. You will see a list of all past charges. Click the download icon next to any invoice to get a PDF copy. Invoices are generated automatically after each successful payment.",
        "intent_tags": ["billing"],
    },
    {
        "question": "The page is not loading correctly",
        "answer": "If a page is not loading correctly, try these steps: (1) Clear your browser cache and cookies, (2) Disable browser extensions temporarily, (3) Try a different browser or incognito mode, (4) Check if you have a stable internet connection. If the issue persists, please share your browser version and a screenshot so we can investigate further.",
        "intent_tags": ["technical"],
    },
    {
        "question": "I keep getting error code 500",
        "answer": "Error 500 is an internal server error. This is usually temporary. Please try refreshing the page after a few minutes. If the error persists, clear your browser cache or try a different browser. Contact our support team with the exact error message, timestamp, and what you were doing when the error occurred.",
        "intent_tags": ["technical"],
    },
    {
        "question": "The mobile app keeps crashing",
        "answer": "If the mobile app keeps crashing, try (1) Force closing and reopening the app, (2) Restarting your device, (3) Checking for app updates in your app store, (4) Reinstalling the app. If crashes continue, please send your device model, OS version, and app version so we can investigate.",
        "intent_tags": ["technical"],
    },
    {
        "question": "How do I integrate your API?",
        "answer": "Our REST API documentation is available at docs.example.com/api. You will need an API key which you can generate in Account Settings > Developer > API Keys. The API supports RESTful endpoints with JSON responses. Rate limits apply at 60 requests per minute for standard plans.",
        "intent_tags": ["technical"],
    },
    {
        "question": "The site is down for me",
        "answer": "We apologize for the disruption. Please check our status page at status.example.com for any ongoing incidents. You can also try accessing the site from a different network or device. If the issue is isolated to you, please run a traceroute and share the results with our support team.",
        "intent_tags": ["technical"],
    },
    {
        "question": "What are your business hours?",
        "answer": "Our support team is available Monday through Friday, 9:00 AM to 6:00 PM EST. For urgent issues, premium customers have 24/7 phone support. You can also reach us via email at support@example.com and we will respond within 24 hours.",
        "intent_tags": ["general"],
    },
    {
        "question": "How do I contact support?",
        "answer": "You can reach our support team via (1) Live chat on our website (fastest), (2) Email at support@example.com (response within 24 hours), (3) Phone at 1-800-555-0123 during business hours, or (4) Submit a support ticket through your account dashboard.",
        "intent_tags": ["general"],
    },
    {
        "question": "Where can I find documentation?",
        "answer": "Our documentation is available at docs.example.com. It includes API documentation, integration guides, user manuals, video tutorials, and FAQs. You can search by keyword or browse by category. We update our documentation regularly with each release.",
        "intent_tags": ["general"],
    },
    {
        "question": "Do you have a mobile app?",
        "answer": "Yes, we have mobile apps for both iOS and Android. You can download our iOS app from the App Store and our Android app from Google Play Store. The mobile app includes all core features plus push notifications and mobile-specific features like fingerprint login.",
        "intent_tags": ["general"],
    },
]


def seed_faqs(db_session: SASession) -> int:
    existing_count = db_session.query(FAQEntry).count()
    if existing_count > 0:
        logger.info("FAQ table already has %d entries, skipping seed", existing_count)
        return 0

    added = 0
    for faq_data in SEED_FAQS:
        existing = (
            db_session.query(FAQEntry)
            .filter(FAQEntry.question == faq_data["question"])
            .first()
        )
        if existing:
            continue

        entry = FAQEntry(
            question=faq_data["question"],
            answer=faq_data["answer"],
            intent_tags_list=faq_data["intent_tags"],
        )
        db_session.add(entry)
        added += 1

    if added > 0:
        db_session.commit()
        logger.info("Seeded %d FAQ entries", added)

    return added
