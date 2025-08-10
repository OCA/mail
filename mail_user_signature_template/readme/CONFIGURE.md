**Prerequisites:**
- The `social_media` module must be installed to use social media links in signatures

To configure signature templates:

1.  Navigate to **Settings \> General Settings \> Companies**
2.  Select your company and go to the "Email Signatures" tab
3.  Enable "Use Signature Templates"
4.  Optionally set a default template for new users
5.  Optionally enable "Force Signature Template" to prevent users from
    using custom signatures
6.  Configure logo settings:
    - **Signature Logo URL (Override)**: Optional external URL to override the default company logo
    - **Logo Display Width/Height**: Display dimensions (default: 120x40)
    
**Logo Behavior:**
- Logos and avatars are served through public endpoints (/mailcdn/) for Gmail compatibility
- No authentication required, ensuring images display properly in all email clients
- Secure token-based URLs prevent unauthorized access
- The Signature Logo URL field allows you to override with a custom external URL
- External URLs can still be used for CDN-hosted logos

**Logo Best Practices (for external URLs):**
- Host logo on your domain (e.g., https://cdn.company.com/logo-email.png)
- Use PNG format with transparent background
- Keep file size under 40KB
- Create at 2x dimensions (e.g., 240x80px) but display at 120x40px

To create signature templates:

1.  Go to **Settings \> Technical \> Email \> Signature Templates**
2.  Click "Create" and design your template using the available
    placeholders
3.  Use the HTML editor to format your signature
4.  Preview your template with the "Preview" button

**UTM Tracking Configuration:**

To enable click tracking in email signatures:

1. Enable "Use UTM Tracking" in the template
2. Configure UTM parameters:
   - **Source**: Defaults to 'email-signature' if not set
   - **Medium**: Defaults to 'email' if not set  
   - **Campaign**: Optional, use for specific marketing campaigns
3. Use `<t t-out="website_url"/>` instead of `<t t-out="website"/>` in templates
4. The system automatically adds user ID as utm_content for granular tracking

Available placeholders (QWeb syntax):

-   `<t t-out="name"/>` - User's display name
-   `<t t-out="email"/>` - User's email address
-   `<t t-out="phone"/>` - User's phone number
-   `<t t-out="mobile"/>` - User's mobile number
-   `<t t-out="function"/>` - User's job position
-   `<t t-out="company_name"/>` - Company name
-   `<t t-out="website"/>` - Company website
-   `<t t-out="company_email"/>` - Company email
-   `<t t-out="company_phone"/>` - Company phone
-   `<t t-out="company_logo"/>` - Company logo (if enabled in template)
-   `<t t-out="user_image"/>` - User avatar image (64x64 circle)
-   `<t t-out="website_url"/>` - Company website URL with optional UTM tracking
-   `<t t-out="social_twitter"/>` - Company Twitter/X URL
-   `<t t-out="social_facebook"/>` - Company Facebook URL
-   `<t t-out="social_linkedin"/>` - Company LinkedIn URL
-   `<t t-out="social_instagram"/>` - Company Instagram URL
-   `<t t-out="social_youtube"/>` - Company YouTube URL
-   `<t t-out="social_github"/>` - Company GitHub URL
