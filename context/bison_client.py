import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, urlencode


class BisonClient:
    """
    A client for the Email Bison API.
    """

    def __init__(self, api_key=None, dotenv_path=None):
        """
        Initializes the BisonClient.
        :param api_key: Your Email Bison API key. If not provided, it will be read from the .env file.
        :param dotenv_path: Path to your .env file. Defaults to a .env file in the same directory as this script.
        """
        if not api_key:
                try:
                    load_dotenv()
                except: 
                    try: 
                        load_dotenv('bison_api/.env')
                    except:
                        raise ValueError("BISON_API_KEY not found. Pass it as an argument or set it in the .env file.")
                
        self.api_key = api_key or os.getenv("BISON_API_KEY")
        
        if not self.api_key:
            raise ValueError("BISON_API_KEY not found. Pass it as an argument or set it in the .env file.")

        self.base_url = "https://bison.mintleads.io/api"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.active_workspace_id = None  # Track the current workspace context
        self.active_workspace_name = None
        self.workspace_id_name_map = {}  # Map workspace_id to workspace_name
        self._initialize_workspace_map()

    def _initialize_workspace_map(self):
        """
        Initializes the workspace_id_name_map by fetching all workspaces.
        """
        try:
            workspaces = self.list_workspaces(paginate=True)
            # If the API returns a dict with 'data', extract from there
            if isinstance(workspaces, dict) and 'data' in workspaces:
                workspaces = workspaces['data']
            self.workspace_id_name_map = {ws['id']: ws['name'] for ws in workspaces if 'id' in ws and 'name' in ws}
        except Exception as e:
            self.workspace_id_name_map = {}

    @property
    def active_workspace(self):
        """
        Returns a dict {workspace_id: workspace_name} for the current active workspace.
        """
        if self.active_workspace_id and self.workspace_id_name_map:
            name = self.workspace_id_name_map.get(self.active_workspace_id)
            if name:
                return {self.active_workspace_id: name}
        return None

    def _handle_response(self, response):
        """
        Handles the HTTP response from the API.
        :param response: The response object.
        :return: The JSON response if successful, otherwise raises an HTTPError.
        """
        response.raise_for_status()
        if response.status_code == 204:  # No Content
            return {}

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json()
        elif 'text/plain' in content_type:
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                return response.text
        return response.content

    def _get(self, endpoint, params=None):
        response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params)
        return self._handle_response(response)

    def _post(self, endpoint, data=None, files=None, timeout=None):
        headers = self.headers.copy()
        if files:
            del headers["Content-Type"]  # requests will set it with boundary
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                data=data,
                files=files,
                timeout=timeout,
            )
        else:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                json=data,
                timeout=timeout,
            )
        return self._handle_response(response)

    def _put(self, endpoint, data=None):
        response = requests.put(f"{self.base_url}/{endpoint}", headers=self.headers, json=data)
        return self._handle_response(response)

    def _patch(self, endpoint, data=None):
        response = requests.patch(f"{self.base_url}/{endpoint}", headers=self.headers, json=data)
        return self._handle_response(response)

    def _delete(self, endpoint, data=None):
        response = requests.delete(f"{self.base_url}/{endpoint}", headers=self.headers, json=data)
        return self._handle_response(response)

    def _get_all(self, endpoint, params=None):
        """
        Performs a GET request and handles pagination to retrieve all items from all pages.
        """
        all_items = []
        page_count = 0
        
        # Make the first request
        response_data = self._get(endpoint, params)
        page_count += 1
        
        if 'data' in response_data:
            retrieved_data = response_data['data']
            if isinstance(retrieved_data, list):
                all_items.extend(retrieved_data)
                # print(f"    📄 Page {page_count}: Retrieved {len(retrieved_data)} items (Total: {len(all_items)})")
            else:
                all_items.append(retrieved_data)
                # print(f"    📄 Page {page_count}: Retrieved 1 item (Total: {len(all_items)})")

        next_page_url = response_data.get('links', {}).get('next')
        
        while next_page_url:
            # For subsequent pages, we need to preserve the original parameters
            # Parse the next_page_url and append the original params
            parsed_url = urlparse(next_page_url)
            existing_params = parse_qs(parsed_url.query)
            
            # Convert existing params from list format to single values
            existing_params_single = {}
            for key, value_list in existing_params.items():
                existing_params_single[key] = value_list[0] if value_list else ''
            
            # Merge with original params, original params take precedence
            if params:
                merged_params = {**existing_params_single, **params}
            else:
                merged_params = existing_params_single
            
            # Reconstruct the URL with merged parameters
            if merged_params:
                query_string = urlencode(merged_params)
                full_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{query_string}"
            else:
                full_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            
            # Make the request with the reconstructed URL
            response = requests.get(full_url, headers=self.headers)
            response_data = self._handle_response(response)
            page_count += 1
            
            if 'data' in response_data:
                retrieved_data = response_data['data']
                if isinstance(retrieved_data, list):
                    all_items.extend(retrieved_data)
                    # print(f"    📄 Page {page_count}: Retrieved {len(retrieved_data)} items (Total: {len(all_items)})")
                else:
                    all_items.append(retrieved_data)
                    # print(f"    📄 Page {page_count}: Retrieved 1 item (Total: {len(all_items)})")
            
            next_page_url = response_data.get('links', {}).get('next')
            
        # print(f"    🏁 Pagination complete: {page_count} pages, {len(all_items)} total items")
        return all_items

    # =================================================================
    # Account Management
    # =================================================================

    def account_details(self):
        """This endpoint retrieves the details of the authenticated user."""
        return self._get("users")

    def update_profile_picture(self, photo_path):
        """This endpoint allows the authenticated user to update their profile picture."""
        with open(photo_path, 'rb') as f:
            files = {'photo': (os.path.basename(photo_path), f)}
            return self._post("users/profile-picture", files=files)

    def update_password(self, current_password, new_password, password_confirmation):
        """This endpoint allows the authenticated user to update their password."""
        payload = {
            "current_password": current_password,
            "password": new_password,
            "password_confirmation": password_confirmation,
        }
        return self._put("users/password", data=payload)

    def generate_headless_ui_token(self):
        """Generate headless UI token (beta)"""
        return self._post("users/headless-ui-token")

    # =================================================================
    # Campaigns
    # =================================================================

    def list_campaigns(self, search=None, status=None, tag_ids=None, paginate=True):
        """This endpoint retrieves all of the authenticated user's campaigns."""
        params = {}
        if search:
            params['search'] = search
        if status:
            params['status'] = status
        if tag_ids:
            params['tag_ids'] = tag_ids
        
        if paginate:
            return self._get_all("campaigns", params=params)
        return self._get("campaigns", params=params)

    def create_campaign(self, name, campaign_type='outbound'):
        """This endpoint allows the authenticated user to create a new campaign."""
        payload = {"name": name, "type": campaign_type}
        return self._post("campaigns", data=payload)

    def pause_campaign(self, campaign_id):
        """This endpoint allows the authenticated user to pause a campaign."""
        return self._patch(f"campaigns/{campaign_id}/pause")

    def resume_campaign(self, campaign_id):
        """This endpoint allows the authenticated user to resume a paused campaign."""
        return self._patch(f"campaigns/{campaign_id}/resume")

    def archive_campaign(self, campaign_id):
        """This endpoint allows the authenticated user to archive a campaign."""
        return self._patch(f"campaigns/{campaign_id}/archive")

    def update_campaign_settings(self, campaign_id, settings):
        """This endpoint allows the authenticated user to update the settings of a campaign."""
        return self._patch(f"campaigns/{campaign_id}/update", data=settings)

    def create_campaign_schedule(self, campaign_id, schedule):
        """This endpoint allows the authenticated user to create the schedule of the campaign."""
        return self._post(f"campaigns/{campaign_id}/schedule", data=schedule)

    def view_campaign_schedule(self, campaign_id):
        """This endpoint allows the authenticated user to view the schedule of the campaign."""
        return self._get(f"campaigns/{campaign_id}/schedule")

    def update_campaign_schedule(self, campaign_id, schedule):
        """This endpoint allows the authenticated user to update the schedule of the campaign."""
        return self._put(f"campaigns/{campaign_id}/schedule", data=schedule)

    def view_all_schedule_templates(self):
        """This endpoint allows the authenticated user to view their scheduled templates."""
        return self._get("campaigns/schedule/templates")

    def view_all_available_schedule_timezones(self):
        """This endpoint allows the authenticated user to view all available timezones."""
        return self._get("campaigns/schedule/available-timezones")

    def show_sending_schedules_for_campaigns(self, day):
        """This endpoint allows the authenticated user to view the sending schedules for campaigns"""
        return self._post("campaigns/sending-schedules", data={"day": day})

    def show_sending_schedule_for_campaign(self, campaign_id, day):
        """This endpoint allows the authenticated user to view the sending schedule of a single campaign"""
        return self._post(f"campaigns/{campaign_id}/sending-schedule", data={"day": day})

    def create_campaign_schedule_from_template(self, campaign_id, schedule_id):
        """This endpoint allows the authenticated user to create the schedule of the campaign from a template."""
        return self._post(f"campaigns/{campaign_id}/create-schedule-from-template", data={"schedule_id": schedule_id})

    def view_campaign_sequence_steps(self, campaign_id):
        """This endpoint allows the authenticated user to view the sequence steps of the campaign."""
        return self._get(f"campaigns/{campaign_id}/sequence-steps")

    def create_sequence_steps(self, campaign_id, title, sequence_steps):
        """This endpoint allows the authenticated user to create the campaign sequence steps from scratch."""
        payload = {
            "title": title,
            "sequence_steps": sequence_steps
        }
        return self._post(f"campaigns/{campaign_id}/sequence-steps", data=payload)

    def update_sequence_steps(self, sequence_id, title, sequence_steps):
        """This endpoint allows the authenticated user to update the campaign sequence steps."""
        payload = {
            "title": title,
            "sequence_steps": sequence_steps
        }
        return self._put(f"campaigns/sequence-steps/{sequence_id}", data=payload)

    def delete_sequence_step(self, sequence_step_id):
        """This endpoint allows the authenticated user to delete a specific sequence step from a sequence"""
        return self._delete(f"campaigns/sequence-steps/{sequence_step_id}")

    def send_sequence_step_test_email(self, sequence_step_id, sender_email_id, to_email, use_dedicated_ips=False):
        """This endpoint allows the authenticated user to send a test email from a sequence step."""
        payload = {
            "sender_email_id": sender_email_id,
            "to_email": to_email,
            "use_dedicated_ips": use_dedicated_ips
        }
        return self._post(f"campaigns/sequence-steps/{sequence_step_id}/test-email", data=payload)

    def get_campaign_replies(self, campaign_id, search=None, status=None, folder=None, read=None, sender_email_id=None, lead_id=None, tag_ids=None):
        """This endpoint retrieves all replies associated with a campaign."""
        params = {}
        if search: params['search'] = search
        if status: params['status'] = status
        if folder: params['folder'] = folder
        if read is not None: params['read'] = read
        if sender_email_id: params['sender_email_id'] = sender_email_id
        if lead_id: params['lead_id'] = lead_id
        if tag_ids: params['tag_ids'] = tag_ids
        return self._get(f"campaigns/{campaign_id}/replies", params=params)

    def get_all_leads_for_campaign(self, campaign_id):
        """This endpoint retrieves all leads associated with a campaign."""
        return self._get(f"campaigns/{campaign_id}/leads")

    def remove_leads_from_campaign(self, campaign_id, lead_ids):
        """This endpoint allows the authenticated user to remove leads from a campaign."""
        return self._delete(f"campaigns/{campaign_id}/leads", data={"lead_ids": lead_ids})

    def import_leads_from_existing_list(self, campaign_id, lead_list_id):
        """This endpoint allows the authenticated user to import leads from an existing list into a campaign."""
        return self._post(f"campaigns/{campaign_id}/leads/attach-lead-list", data={"lead_list_id": lead_list_id})

    def import_leads_by_ids(self, campaign_id, lead_ids):
        """This endpoint allows the authenticated user to import leads by their IDs into a campaign."""
        return self._post(f"campaigns/{campaign_id}/leads/attach-leads", data={"lead_ids": lead_ids})

    def stop_future_emails_for_leads(self, campaign_id, lead_ids):
        """This endpoint allows the authenticated user to stop future emails for selected leads in a campaign"""
        return self._post(f"campaigns/{campaign_id}/leads/stop-future-emails", data={"lead_ids": lead_ids})

    def get_all_scheduled_emails_for_campaign(self, campaign_id, status=None, scheduled_date=None, scheduled_date_local=None, paginate=True):
        """This endpoint retrieves all scheduled emails associated with a campaign."""
        params = {}
        if status: params['status'] = status
        if scheduled_date: params['scheduled_date'] = scheduled_date
        if scheduled_date_local: params['scheduled_date_local'] = scheduled_date_local
        
        endpoint = f"campaigns/{campaign_id}/scheduled-emails"
        if paginate:
            return self._get_all(endpoint, params=params)
        return self._get(endpoint, params=params)

    def get_all_campaign_sender_emails(self, campaign_id):
        """This endpoint retrieves all email accounts (sender emails) associated with a campaign"""
        return self._get(f"campaigns/{campaign_id}/sender-emails")

    def get_campaign_stats_summary(self, campaign_id, start_date, end_date):
        """This endpoint retrieves the statistics of all your campaigns."""
        payload = {
            "start_date": start_date,
            "end_date": end_date
        }
        return self._post(f"campaigns/{campaign_id}/stats", data=payload)

    def import_sender_emails_by_id(self, campaign_id, sender_email_ids):
        """This endpoint allows the authenticated user to attach sender emails to a campaign."""
        return self._post(f"campaigns/{campaign_id}/attach-sender-emails", data={"sender_email_ids": sender_email_ids})

    def remove_sender_emails_by_id(self, campaign_id, sender_email_ids):
        """This endpoint allows the authenticated user to remove sender emails from a draft or paused campaign."""
        return self._delete(f"campaigns/{campaign_id}/remove-sender-emails", data={"sender_email_ids": sender_email_ids})

    def get_campaign_line_area_chart_stats(self, campaign_id, start_date, end_date):
        """This endpoint retrieves stats by date for a given period, for this campaign"""
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        return self._get(f"campaigns/{campaign_id}/line-area-chart-stats", params=params)

    def campaign_details(self, campaign_id):
        """This endpoint retrieves the details of a specific campaign."""
        return self._get(f"campaigns/{campaign_id}")
    
    # =================================================================
    # Replies
    # =================================================================

    def get_all_replies(self, search=None, status=None, folder=None, read=None, campaign_id=None, sender_email_id=None, lead_id=None, tag_ids=None):
        """
        Retrieve all replies for the authenticated user.
        """
        params = {}
        if search: params['search'] = search
        if status: params['status'] = status
        if folder: params['folder'] = folder
        if read is not None: params['read'] = read
        if campaign_id: params['campaign_id'] = campaign_id
        if sender_email_id: params['sender_email_id'] = sender_email_id
        if lead_id: params['lead_id'] = lead_id
        if tag_ids:
            for i, tag_id in enumerate(tag_ids):
                params[f'tag_ids[{i}]'] = tag_id
        return self._get_all("replies", params=params)

    def get_reply(self, reply_id):
        """
        Retrieve a specific reply by its ID.
        """
        return self._get(f"replies/{reply_id}")

    def compose_new_email(self, subject, message, sender_email_id, to_emails, use_dedicated_ips=True, content_type="html", cc_emails=None, bcc_emails=None):
        """
        Send a one-off email in a new email thread.
        """
        payload = {
            "subject": subject,
            "message": message,
            "sender_email_id": sender_email_id,
            "use_dedicated_ips": use_dedicated_ips,
            "content_type": content_type,
            "to_emails": to_emails
        }
        if cc_emails:
            payload["cc_emails"] = cc_emails
        if bcc_emails:
            payload["bcc_emails"] = bcc_emails
        return self._post("replies/new", data=payload)

    def create_reply(self, reply_id, message, sender_email_id, to_emails, inject_previous_email_body=True, use_dedicated_ips=True, content_type="html", cc_emails=None, bcc_emails=None):
        """
        Reply to an existing email.
        """
        payload = {
            "inject_previous_email_body": inject_previous_email_body,
            "message": message,
            "use_dedicated_ips": use_dedicated_ips,
            "sender_email_id": sender_email_id,
            "content_type": content_type,
            "to_emails": to_emails
        }
        if cc_emails:
            payload["cc_emails"] = cc_emails
        if bcc_emails:
            payload["bcc_emails"] = bcc_emails
        return self._post(f"replies/{reply_id}/reply", data=payload)

    def forward_reply(self, reply_id, message, sender_email_id, to_emails, inject_previous_email_body=True, content_type="html", cc_emails=None, bcc_emails=None, use_dedicated_ips=True):
        """
        Forward an existing reply.
        """
        payload = {
            "inject_previous_email_body": inject_previous_email_body,
            "message": message,
            "use_dedicated_ips": use_dedicated_ips,
            "sender_email_id": sender_email_id,
            "content_type": content_type,
            "to_emails": to_emails
        }
        if cc_emails:
            payload["cc_emails"] = cc_emails
        if bcc_emails:
            payload["bcc_emails"] = bcc_emails
        return self._post(f"replies/{reply_id}/forward", data=payload)

    def mark_reply_as_interested(self, reply_id):
        """
        Mark a specific reply as interested.
        """
        return self._patch(f"replies/{reply_id}/mark-as-interested")

    def mark_reply_as_not_interested(self, reply_id):
        """
        Mark a specific reply as not interested.
        """
        return self._patch(f"replies/{reply_id}/mark-as-not-interested")

    def unsubscribe_reply_contact(self, reply_id):
        """
        Unsubscribe the contact associated with a specific reply from scheduled emails.
        """
        return self._patch(f"replies/{reply_id}/unsubscribe")

    def delete_reply(self, reply_id):
        """
        Delete a specific reply by its ID.
        """
        return self._delete(f"replies/{reply_id}")

    def get_reply_conversation_thread(self, reply_id):
        """
        Get a reply object with all previous and newer messages to build out an email thread.
        """
        return self._get(f"replies/{reply_id}/conversation-thread")

    def attach_scheduled_email_to_reply(self, reply_id, scheduled_email_id):
        """
        Attach a scheduled email to a reply (and lead).
        """
        payload = {"scheduled_email_id": scheduled_email_id}
        return self._post(f"replies/{reply_id}/attach-scheduled-email-to-reply", data=payload)

    def push_reply_to_followup_campaign(self, reply_id, campaign_id, force_add_reply=True):
        """
        Push a reply (and lead) to a reply followup campaign.
        """
        payload = {"campaign_id": campaign_id, "force_add_reply": force_add_reply}
        return self._post(f"replies/{reply_id}/followup-campaign/push", data=payload)

    # =================================================================
    # Email Accounts
    # =================================================================

    def list_email_accounts(self, search=None, tag_ids=None, paginate=True):
        """Retrieves a collection of email accounts associated with the authenticated workspace."""
        params = {}
        if search:
            params['search'] = search
        if tag_ids:
            params['tag_ids'] = tag_ids

        if paginate:
            return self._get_all("sender-emails", params=params)
        return self._get("sender-emails", params=params)

    def show_email_account_campaigns(self, sender_email_id):
        """Retrieves a collection of campaigns where this email account is being used"""
        return self._get(f"sender-emails/{sender_email_id}/campaigns")

    def show_email_account_details(self, sender_email_id):
        """Retrieves details of a specific email account."""
        return self._get(f"sender-emails/{sender_email_id}")

    def update_sender_email(self, sender_email_id, daily_limit=None, name=None, email_signature=None):
        """Update the settings for a specified sender email."""
        payload = {}
        if daily_limit is not None:
            payload['daily_limit'] = daily_limit
        if name is not None:
            payload['name'] = name
        if email_signature is not None:
            payload['email_signature'] = email_signature
        return self._patch(f"sender-emails/{sender_email_id}", data=payload)

    def delete_email_account(self, sender_email_id):
        """Delete email account."""
        return self._delete(f"sender-emails/{sender_email_id}")

    # =================================================================
    # Workspaces v1.1
    # =================================================================

    def list_workspaces(self, paginate=True):
        """This endpoint retrieves all of the authenticated user's workspaces."""
        if paginate:
            return self._get_all("workspaces/v1.1")
        return self._get("workspaces/v1.1")

    def create_workspace(self, name):
        """This endpoint allows the authenticated user to create a new workspace."""
        return self._post("workspaces/v1.1", data={'name': name})

    def create_user_and_add_to_workspace(self, name, password, email, role):
        """Create a new user on your instance, and add them to the current workspace."""
        payload = {
            "name": name,
            "password": password,
            "email": email,
            "role": role
        }
        return self._post("workspaces/v1.1/users", data=payload)

    def create_api_token_for_workspace(self, team_id, name):
        """This endpoint lets you create an API token for a given workspace"""
        return self._post(f"workspaces/v1.1/{team_id}/api-tokens", data={'name': name})

    def switch_workspace(self, team_id):
        """
        Switches the active workspace context to the given team_id.
        Updates self.active_workspace_id and refreshes workspace_id_name_map on success.
        """
        response = self._post("workspaces/v1.1/switch-workspace", data={"team_id": team_id})
        # If successful, update the active_workspace_id
        if response and response.get('status') == 'success':
            self.active_workspace_id = team_id
            self.active_workspace_name = self.workspace_id_name_map[team_id]
        elif response and 'data' in response and response['data'].get('id') == team_id:
            self.active_workspace_id = team_id
            self.active_workspace_name = self.workspace_id_name_map[team_id]
        # Refresh the workspace map after switching
        self._initialize_workspace_map()

        return response

    def invite_team_member(self, email, role):
        """This endpoint allows the authenticated user to invite a new member to their team."""
        payload = {"email": email, "role": role}
        return self._post("workspaces/v1.1/invite-members", data=payload)

    def accept_workspace_invitation(self, team_invitation_id):
        """This endpoint allows the user to accept an invitation to join a workspace."""
        return self._post(f"workspaces/v1.1/accept/{team_invitation_id}")

    def delete_workspace_member(self, user_id):
        """This endpoint allows the authenticated user to remove a workspace member."""
        return self._delete(f"workspaces/v1.1/members/{user_id}")

    def get_workspace_stats_summary(self, start_date, end_date):
        """This endpoint retrieves overall stats for this workspace between two given dates."""
        params = {"start_date": start_date, "end_date": end_date}
        return self._get("workspaces/v1.1/stats", params=params)

    def get_workspace_line_area_chart_stats(self, start_date, end_date):
        """This endpoint retrieves stats by date for a given period"""
        params = {"start_date": start_date, "end_date": end_date}
        return self._get("workspaces/v1.1/line-area-chart-stats", params=params)

    def update_workspace(self, team_id, name):
        """This endpoint allows the authenticated user to update their workspace information"""
        return self._put(f"workspaces/v1.1/{team_id}", data={'name': name})

    def workspace_details(self, team_id):
        """This endpoint retrieves the details of the authenticated user's workspace."""
        return self._get(f"workspaces/v1.1/{team_id}")

    # =================================================================
    # Warmup
    # =================================================================

    def list_email_accounts_with_warmup_stats(self, start_date, end_date, search=None, tag_ids=None, warmup_status=None, mx_records_status=None, paginate=False):
        """Retrieves a collection of email accounts associated with the authenticated workspace, along with their warmup stats"""
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        if search:
            params['search'] = search
        if tag_ids:
            params['tag_ids'] = tag_ids
        if warmup_status:
            params['warmup_status'] = warmup_status
        if mx_records_status:
            params['mx_records_status'] = mx_records_status
        
        if paginate:
            return self._get_all("warmup/sender-emails", params=params)
        return self._get("warmup/sender-emails", params=params)

    def enable_warmup_for_email_accounts(self, sender_email_ids):
        """This endpoint enables warmup for all the selected email accounts"""
        return self._patch("warmup/sender-emails/enable", data={"sender_email_ids": sender_email_ids})

    def disable_warmup_for_email_accounts(self, sender_email_ids):
        """This endpoint disables warmup for all the selected email accounts"""
        return self._patch("warmup/sender-emails/disable", data={"sender_email_ids": sender_email_ids})

    def update_daily_warmup_limits_for_email_accounts(self, sender_email_ids, daily_limit, daily_reply_limit):
        """This endpoint updates the daily warmup limits for selected email accounts"""
        payload = {
            "sender_email_ids": sender_email_ids,
            "daily_limit": daily_limit,
            "daily_reply_limit": daily_reply_limit
        }
        return self._patch("warmup/sender-emails/update-daily-warmup-limits", data=payload)

    def show_single_email_account_with_warmup_details(self, sender_email_id, start_date, end_date):
        """Retrieves a single email account (sender email) with its warmup details"""
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        return self._get(f"warmup/sender-emails/{sender_email_id}", params=params)

    # =================================================================
    # Webhooks
    # =================================================================

    def list_webhooks(self):
        """Retrieve a list of all webhooks for the authenticated user's workspace."""
        return self._get("webhook-url")

    def get_webhook(self, webhook_id):
        """Get the details of a specific webhook."""
        return self._get(f"webhook-url/{webhook_id}")

    def create_webhook(self, name, url, events):
        """Store a new webhook for the authenticated user's workspace.
        Args:
            name: Name of the webhook
            url: URL endpoint to send webhook events to
            events: List of event types to enable for this webhook
        """
        payload = {
            "name": name,
            "url": url,
            "events": events
        }
        return self._post("webhook-url", data=payload)

    def update_webhook(self, webhook_id, name=None, url=None, events=None):
        """Modify an existing webhook's details.
        Args:
            webhook_id: ID of the webhook to update
            name: Optional new name for the webhook
            url: Optional new URL for the webhook
            events: Optional list of events to enable (events not included will be disabled)
        """
        payload = {}
        if name is not None:
            payload["name"] = name
        if url is not None:
            payload["url"] = url
        if events is not None:
            payload["events"] = events
        return self._put(f"webhook-url/{webhook_id}", data=payload)

    def delete_webhook(self, webhook_id):
        """Remove a webhook url by its ID."""
        return self._delete(f"webhook-url/{webhook_id}")

    # =================================================================
    # Webhook Events
    # =================================================================

    def get_webhook_event_types(self):
        """Shows you a list of all valid webhook event types that are supported"""
        return self._get("webhook-events/event-types")

    def get_sample_webhook_payload(self, event_type):
        """Get a sample webhook event payload for a specific event type"""
        payload = {"event_type": event_type}
        return self._post("webhook-events/sample-payload", data=payload)

    def send_test_webhook(self, event_type, url):
        """Send a test webhook for a chosen event type"""
        payload = {
            "event_type": event_type,
            "url": url
        }
        return self._post("webhook-events/test-event", data=payload)

    # =================================================================
    # Custom Lead Variables
    # =================================================================

    def list_custom_variables(self):
        """Retrieve a list of all custom variables for your workspace"""
        return self._get("custom-variables")

    def create_custom_variable(self, name):
        """Add a new custom variable for your workspace"""
        return self._post("custom-variables", data={"name": name})

    def bulk_import_leads_csv(self, name, csv_content, columns_to_map, filename="leads.csv", columns_map_format="indexed_underscore"):
        """Bulk import leads using CSV content.
        Args:
            name: The name of the contact list
            csv_content: CSV content as string (e.g., from pd.read_csv().to_csv())
            columns_to_map: Dictionary mapping Bison fields to CSV headers
            filename: Optional filename for the CSV (default: "leads.csv")
            columns_map_format: One of 'indexed_underscore', 'indexed_space', 'nonindexed_underscore', 'nonindexed_space', 'both'
        """
        # Convert CSV content to bytes if it's a string
        if isinstance(csv_content, str):
            csv_content = csv_content.encode('utf-8')
        files = {'csv': (filename, csv_content, 'text/csv')}
        data = {'name': name}
        # Add column mappings in the requested format
        for bison_field, csv_header in columns_to_map.items():
            if columns_map_format == "indexed_underscore":
                data[f'columnsToMap[0][{bison_field}]'] = csv_header
            elif columns_map_format == "indexed_space":
                field_name = bison_field.replace('_', ' ')
                data[f'columnsToMap[0][{field_name}]'] = csv_header
            elif columns_map_format == "nonindexed_underscore":
                data[f'columnsToMap[{bison_field}]'] = csv_header
            elif columns_map_format == "nonindexed_space":
                field_name = bison_field.replace('_', ' ')
                data[f'columnsToMap[{field_name}]'] = csv_header
            elif columns_map_format == "both":
                data[f'columnsToMap[0][{bison_field}]'] = csv_header
                data[f'columnsToMap[{bison_field}]'] = csv_header
                field_name = bison_field.replace('_', ' ')
                data[f'columnsToMap[0][{field_name}]'] = csv_header
                data[f'columnsToMap[{field_name}]'] = csv_header
        return self._post("leads/bulk/csv", data=data, files=files)

    def create_multiple_leads(self, leads):
        """Create multiple lead records in a single request using the api/leads/multiple endpoint.
        Args:
            leads: List of lead dictionaries. Each lead should contain fields like:
                  first_name, last_name, email, title, company, custom_variables
                  Limit: 500 leads per request
        """
        payload = {"leads": leads}
        return self._post("leads/multiple", data=payload)

    def create_or_update_multiple_leads(self, leads, timeout=None):
        """Update or create multiple lead records in a single request using the api/leads/create-or-update/multiple endpoint.
        Args:
            leads: List of lead dictionaries. Each lead should contain fields like:
                  first_name, last_name, email, title, company, custom_variables
                  Limit: 500 leads per request
        """
        payload = {"leads": leads}
        return self._post("leads/create-or-update/multiple", data=payload, timeout=timeout)

    def get_campaign_events_stats(self, start_date, end_date, sender_email_ids=None, campaign_ids=None):
        """Get campaign events stats for a given date range.
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            sender_email_ids: Optional list of sender email IDs to filter by
            campaign_ids: Optional list of campaign IDs to filter by
        Returns:
            Dictionary containing stats data with events like 'Replied', 'Total Opens', 'Unique Opens', 'Sent', 'Bounced', 'Unsubscribed', 'Interested'
        """
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Add sender email IDs if provided
        if sender_email_ids:
            for i, email_id in enumerate(sender_email_ids):
                params[f"sender_email_ids[{i}]"] = email_id
        
        # Add campaign IDs if provided
        if campaign_ids:
            for i, campaign_id in enumerate(campaign_ids):
                params[f"campaign_ids[{i}]"] = campaign_id
        
        return self._get("campaign-events/stats", params=params)

    # ... and so on for all other tags from the OpenAPI spec.


if __name__ == '__main__':
    # Make sure you have a .env file in the same directory as this script,
    # or in your project root, with the BISON_API_KEY set.
    # e.g., BISON_API_KEY=your_api_key_here

    client = BisonClient()

    try:
        print("Fetching account details...")
        account_details = client.account_details()
        print(json.dumps(account_details, indent=2))
        print("-" * 20)

        print("Listing campaigns...")
        campaigns = client.list_campaigns()
        print(json.dumps(campaigns, indent=2))
        print("-" * 20)

        print("Listing email accounts...")
        email_accounts = client.list_email_accounts()
        print(json.dumps(email_accounts, indent=2))
        print("-" * 20)

        print("Listing workspaces...")
        workspaces = client.list_workspaces()
        print(json.dumps(workspaces, indent=2))
        print("-" * 20)


    except requests.exceptions.HTTPError as e:
        print(f"An HTTP error occurred: {e}")
        print(f"Response body: {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}") 