The administrator only has to set things up once:

1. Go to *Settings → General Settings → Discuss* and enable **Use Custom Email
   Servers**, then enable **Support Outlook Authentication** and fill in the
   Outlook **Client ID** and **Client Secret** of your registered Azure
   application.
2. In the Azure app registration:
   - Add the redirect URI `<your-odoo-base-url>/microsoft_outlook/confirm`.
   - Add the delegated permission **Office 365 Exchange Online → `SMTP.Send`**
     and grant **admin consent** for the tenant, so every user can authenticate
     without being blocked.
3. In Exchange Online, make sure **Authenticated SMTP** (SMTP AUTH) is enabled
   for each mailbox that will send through Odoo (it is often disabled at tenant
   level):

   ```
   Set-CASMailbox -Identity user@example.com -SmtpClientAuthenticationDisabled $false
   ```

Internal (non-share) users can then connect their own mailbox themselves (see
*Usage*).
