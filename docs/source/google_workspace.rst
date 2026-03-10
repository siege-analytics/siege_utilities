Google Workspace Write APIs
===========================

The Google Workspace integration provides write access to Google Sheets, Docs, Slides,
and Drive via the Google API v4/v1. All operations are authenticated through
``GoogleWorkspaceClient``, which supports OAuth2, service accounts, and multi-account
registry lookup.

.. contents:: On this page
   :local:
   :depth: 2

Installation
------------

.. code-block:: bash

   pip install siege-utilities[analytics]

This installs ``google-api-python-client``, ``google-auth-oauthlib``, and
``google-auth-httplib2``.

Authentication
--------------

All write operations require an authenticated ``GoogleWorkspaceClient``.

1Password Integration (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``from_1password()`` factory method downloads a credential JSON document from
1Password and **auto-detects** whether it is a service account key or an OAuth
client secret:

.. code-block:: python

   from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

   # Service account (server-to-server, no browser required)
   client = GoogleWorkspaceClient.from_1password(
       item_title="Google Service Account - siege_utilities",
       vault="Employee",
       account="Siege_Analytics",
   )

   # OAuth (opens browser on first use, caches token afterward)
   client = GoogleWorkspaceClient.from_1password(
       item_title="Google OAuth Client - siege_utilities",
       vault="Personal",
       account="Siege_Analytics",
   )

**One-time GCP setup for a service account**:

.. code-block:: bash

   # Create the service account
   gcloud iam service-accounts create siege-utilities-workspace \
       --project=windy-art-489721-j3 \
       --display-name="siege_utilities Workspace"

   # Enable Workspace APIs
   gcloud services enable sheets.googleapis.com docs.googleapis.com \
       slides.googleapis.com drive.googleapis.com \
       --project=windy-art-489721-j3

   # Download the JSON key
   gcloud iam service-accounts keys create ~/siege-utilities-sa.json \
       --iam-account=siege-utilities-workspace@windy-art-489721-j3.iam.gserviceaccount.com \
       --project=windy-art-489721-j3

   # Store in 1Password and delete the local file
   op document create ~/siege-utilities-sa.json \
       --title "Google Service Account - siege_utilities" \
       --vault Employee --account Siege_Analytics
   rm ~/siege-utilities-sa.json

**One-time OAuth setup** (for personal Drive access):

.. code-block:: bash

   python scripts/google_workspace_auth.py

This opens a browser for Google sign-in and caches the token at
``~/.siege/tokens/workspace_token.json``.

.. note::

   Service accounts have their own Drive space. To access files in a user's
   personal Drive, share those files with the service account email
   (``siege-utilities-workspace@windy-art-489721-j3.iam.gserviceaccount.com``).

Direct Authentication
~~~~~~~~~~~~~~~~~~~~~

You can also authenticate without 1Password:

**Service account from a file**:

.. code-block:: python

   client = GoogleWorkspaceClient.from_service_account(
       service_account_file="/path/to/service-account.json",
   )

**OAuth2 with explicit credentials**:

.. code-block:: python

   client = GoogleWorkspaceClient.from_oauth(
       client_id="YOUR_CLIENT_ID",
       client_secret="YOUR_CLIENT_SECRET",
       token_file="workspace_token.json",
   )

**From a GoogleAccount registry** (see `Multi-Account Management`_):

.. code-block:: python

   from siege_utilities.config import GoogleAccountRegistry

   registry = GoogleAccountRegistry(config_path=Path("google_accounts.json"))
   client = GoogleWorkspaceClient.from_registry(registry)

Google Sheets
-------------

Create spreadsheets, write and read data, manage tabs, and round-trip DataFrames.

.. code-block:: python

   from siege_utilities.analytics.google_sheets import (
       create_spreadsheet, write_values, read_values, append_rows,
       write_dataframe, read_dataframe, add_sheet,
       get_spreadsheet_metadata, copy_spreadsheet,
   )

   # Create a spreadsheet with named tabs
   spreadsheet_id = create_spreadsheet(client, "Q1 Report", sheet_names=["Data", "Summary"])

   # Write raw values
   write_values(client, spreadsheet_id, "Data!A1", [
       ["Name", "Revenue", "Region"],
       ["Acme", 150000, "Northeast"],
       ["Beta", 230000, "Southeast"],
   ])

   # Append rows after existing data
   append_rows(client, spreadsheet_id, "Data", [["Gamma", 90000, "West"]])

   # Write a pandas DataFrame
   write_dataframe(client, spreadsheet_id, df, sheet_name="Summary")

   # Read it back
   df_round_trip = read_dataframe(client, spreadsheet_id, "Summary")

   # Add a tab
   add_sheet(client, spreadsheet_id, "Notes")

   # Metadata and copy
   meta = get_spreadsheet_metadata(client, spreadsheet_id)
   copy_id = copy_spreadsheet(client, spreadsheet_id, "Q1 Report (Copy)")

Google Slides
-------------

Create presentations, add slides, and populate them with text boxes and images.

.. code-block:: python

   from siege_utilities.analytics.google_slides import (
       create_presentation, get_presentation, copy_presentation,
       add_blank_slide, create_textbox, insert_text, insert_image,
   )

   pres_id = create_presentation(client, "Quarterly Review")

   # Get the default first slide
   pres = get_presentation(client, pres_id)
   title_slide = pres["slides"][0]["objectId"]

   # Add content to it
   create_textbox(client, pres_id, title_slide, "Q1 2026 Review",
                  left=50, top=80, width=600, height=60)

   # Add a new blank slide with content
   slide_id = add_blank_slide(client, pres_id)
   create_textbox(client, pres_id, slide_id, "Revenue grew 23% YoY",
                  left=50, top=100, width=600, height=40)

   # Copy the presentation
   copy_id = copy_presentation(client, pres_id, "Quarterly Review (Draft)")

Google Docs
-----------

Create documents, insert structured content (paragraphs, tables, images),
and perform find/replace operations.

.. code-block:: python

   from siege_utilities.analytics.google_docs import (
       create_document, get_document, copy_document,
       read_document_text, insert_paragraph, insert_text,
       insert_table, insert_image, replace_text,
   )

   doc_id = create_document(client, "Meeting Notes")

   # Insert a heading
   insert_paragraph(client, doc_id, "Action Items", index=1, heading="HEADING_1")

   # Insert body text
   doc = get_document(client, doc_id)
   end = doc["body"]["content"][-1]["endIndex"] - 1
   insert_paragraph(client, doc_id, "Review budget allocations by Friday.", index=end)

   # Insert a table
   doc = get_document(client, doc_id)
   end = doc["body"]["content"][-1]["endIndex"] - 1
   insert_table(client, doc_id, rows=3, cols=2, index=end)

   # Template substitution
   replace_text(client, doc_id, "{{DATE}}", "2026-03-09")

   # Read full text back
   text = read_document_text(client, doc_id)

   # Copy
   copy_id = copy_document(client, doc_id, "Meeting Notes (Archive)")

Drive Utilities
---------------

The ``GoogleWorkspaceClient`` includes Drive operations for files it creates:

.. code-block:: python

   # Copy any file (spreadsheet, doc, presentation)
   new_id = client.copy_file(file_id, "New Title")

   # Share with a user
   client.share_file(file_id, "colleague@example.com", role="writer")

   # Move to a folder
   client.move_to_folder(file_id, folder_id)

Multi-Account Management
-------------------------

The ``GoogleAccount`` model and ``GoogleAccountRegistry`` support managing
multiple Google accounts (OAuth and service account) per user.

.. code-block:: python

   from siege_utilities.config.models.google_account import (
       GoogleAccount, GoogleAccountType, GoogleAccountStatus,
   )
   from siege_utilities.config import GoogleAccountRegistry
   from siege_utilities.config.models.person import Person

   # Create accounts
   oauth_acct = GoogleAccount(
       google_account_id="personal",
       email="user@example.com",
       display_name="Personal",
       account_type=GoogleAccountType.OAUTH,
       is_default=True,
       oauth_integration_name="google-workspace",
       token_file="~/.siege/tokens/token.json",
   )

   svc_acct = GoogleAccount(
       google_account_id="pipeline",
       email="svc@project.iam.gserviceaccount.com",
       display_name="Pipeline SA",
       account_type=GoogleAccountType.SERVICE_ACCOUNT,
       service_account_ref="op://Infra/google-sa/credential",
   )

   # Registry: register, persist, load
   registry = GoogleAccountRegistry()
   registry.register(oauth_acct)
   registry.register(svc_acct)
   registry.save(Path("google_accounts.json"))

   # Build client from registry
   client = GoogleWorkspaceClient.from_registry(registry)

   # Person integration
   person = Person(person_id="dheeraj", name="Dheeraj Chand")
   person.add_google_account(oauth_acct)
   default = person.get_default_google_account()

   # Migrate from legacy OAuthIntegration
   from siege_utilities.config.google_account_registry import migrate_single_account
   migrated = migrate_single_account(legacy_oauth, email="user@example.com")

Notebook
--------

See ``notebooks/18_Google_Workspace.ipynb`` for a full walkthrough using
elect.info onboarding content written to live Google Drive files.

API Reference
-------------

.. automodule:: siege_utilities.analytics.google_workspace
   :members:
   :undoc-members:

.. automodule:: siege_utilities.analytics.google_sheets
   :members:
   :undoc-members:

.. automodule:: siege_utilities.analytics.google_docs
   :members:
   :undoc-members:

.. automodule:: siege_utilities.analytics.google_slides
   :members:
   :undoc-members:
