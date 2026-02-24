# Linode API Scopes

In the [Quick Start](../README.md#quick-start) section, you'll need to set the Linode API token that will be used to manage your other tokens on Linode.

To make it a little less confusing, I'll refer to the token used to manage other tokens as your **"main token"**, and any other tokens will be **"managed token(s)"**

Your **main token** needs to have higher permissions than the **managed token(s)** you're trying to manage with `latr`.

For example, if you want a **managed token** that has the scope `monitor:read_only`, your **main token** needs `account:read_write,monitor:read_write`.

All **main tokens** need `account:read_write` at a minimum, and any other permissions you'll need to assign to your **managed token(s)**.

Take a look at the Linode API documentation for [a full list of OAuth scopes](https://techdocs.akamai.com/linode-api/reference/get-started#oauth-reference).

