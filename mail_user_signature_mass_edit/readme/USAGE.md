1. Give the user the *Signature Mass Edit* access right in Email Marketing.
2. Go to *Email Marketing > Configuration > Signature Mass Edits*.

   Administrators can also access the same records from
   *Settings > Users & Companies > Signature Mass Edits*.
3. Create a new record.
4. Select the company whose internal users must be updated.
5. Optionally select one or more groups to restrict the update to users belonging
   to those groups. Only internal users are updated.
6. Enter the HTML signature template in the *Source* tab. Use the *Preview*
   tab to check the rendered signature.
7. Click *Confirm*.

The signature template is rendered on the `res.users` model. For example:

```html
<p>
  <strong>{{ object.name }}</strong><br/>
  {{ object.company_id.name }}<br/>
  {{ object.email or '' }}
</p>
```
