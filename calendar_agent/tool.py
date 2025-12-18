"""
Google Calendar Tools for LangChain Agent

This module provides calendar management tools using Google Calendar API.
Based on the tested Google Calendar API integration from api_test.py.
"""

import datetime
import os.path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from langchain_core.tools import tool

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    """
    Authenticate and return Google Calendar service object.
    Uses the same authentication flow as api_test.py.
    """
    creds = None
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except HttpError as error:
        raise Exception(f"Failed to build calendar service: {error}")


# Input schemas for tools
class CreateEventInput(BaseModel):
    """Input for creating a calendar event."""
    summary: str = Field(description="Title/summary of the event")
    start_datetime: str = Field(description="Start date and time in ISO format (e.g., '2023-12-25T10:00:00')")
    end_datetime: str = Field(description="End date and time in ISO format (e.g., '2023-12-25T11:00:00')")
    description: Optional[str] = Field(default="", description="Event description")
    location: Optional[str] = Field(default="", description="Event location")
    attendees: Optional[List[str]] = Field(default_factory=list, description="List of attendee email addresses")


class ListEventsInput(BaseModel):
    """Input for listing calendar events."""
    max_results: Optional[int] = Field(default=10, description="Maximum number of events to return")
    time_min: Optional[str] = Field(default=None, description="Lower bound for event start time (ISO format)")
    time_max: Optional[str] = Field(default=None, description="Upper bound for event start time (ISO format)")


class UpdateEventInput(BaseModel):
    """Input for updating a calendar event."""
    event_id: str = Field(description="ID of the event to update")
    summary: Optional[str] = Field(default=None, description="New title/summary of the event")
    start_datetime: Optional[str] = Field(default=None, description="New start date and time in ISO format")
    end_datetime: Optional[str] = Field(default=None, description="New end date and time in ISO format")
    description: Optional[str] = Field(default=None, description="New event description")
    location: Optional[str] = Field(default=None, description="New event location")


class DeleteEventInput(BaseModel):
    """Input for deleting a calendar event."""
    event_id: str = Field(description="ID of the event to delete")


class PostponeEventInput(BaseModel):
    """Input for postponing a calendar event."""
    event_id: str = Field(description="ID of the event to postpone")
    hours_to_postpone: int = Field(description="Number of hours to postpone the event")


# Calendar Tools

@tool(args_schema=CreateEventInput)
def create_event_tool(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = "",
    attendees: List[str] = None
) -> str:
    """
    Create a new calendar event.
    
    Args:
        summary: Title of the event
        start_datetime: Start date and time in ISO format (e.g., '2023-12-25T10:00:00')
        end_datetime: End date and time in ISO format (e.g., '2023-12-25T11:00:00')
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)
    
    Returns:
        Success message with event ID or error message
    """
    try:
        service = get_calendar_service()
        
        # Prepare event data
        event_data = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'UTC',
            },
        }
        
        # Add attendees if provided
        if attendees:
            event_data['attendees'] = [{'email': email} for email in attendees]
        
        # Create the event
        event = service.events().insert(calendarId='primary', body=event_data).execute()
        
        return f"Event created successfully! Event ID: {event.get('id')}. Event link: {event.get('htmlLink')}"
        
    except HttpError as error:
        return f"Error creating event: {error}"
    except Exception as error:
        return f"Unexpected error creating event: {error}"


@tool(args_schema=ListEventsInput)
def list_events_tool(
    max_results: int = 10,
    time_min: str = None,
    time_max: str = None
) -> str:
    """
    List upcoming calendar events.
    
    Args:
        max_results: Maximum number of events to return (default: 10)
        time_min: Lower bound for event start time in ISO format (default: now)
        time_max: Upper bound for event start time in ISO format (optional)
    
    Returns:
        Formatted list of events or error message
    """
    try:
        service = get_calendar_service()
        
        # Use current time as default time_min if not provided
        if time_min is None:
            time_min = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        
        # Prepare query parameters
        query_params = {
            'calendarId': 'primary',
            'timeMin': time_min,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if time_max:
            query_params['timeMax'] = time_max
        
        # Get events
        events_result = service.events().list(**query_params).execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found."
        
        # Format events for display
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'No title')
            location = event.get('location', '')
            event_id = event.get('id', '')
            
            event_info = f"• {summary}"
            event_info += f"\n  📅 Start: {start}"
            event_info += f"\n  ⏰ End: {end}"
            if location:
                event_info += f"\n  📍 Location: {location}"
            event_info += f"\n  🆔 Event ID: {event_id}"
            
            event_list.append(event_info)
        
        return f"Found {len(events)} upcoming events:\n\n" + "\n\n".join(event_list)
        
    except HttpError as error:
        return f"Error listing events: {error}"
    except Exception as error:
        return f"Unexpected error listing events: {error}"


@tool(args_schema=UpdateEventInput)
def update_event_tool(
    event_id: str,
    summary: str = None,
    start_datetime: str = None,
    end_datetime: str = None,
    description: str = None,
    location: str = None
) -> str:
    """
    Update an existing calendar event.
    
    Args:
        event_id: ID of the event to update
        summary: New title of the event (optional)
        start_datetime: New start date and time in ISO format (optional)
        end_datetime: New end date and time in ISO format (optional)
        description: New event description (optional)
        location: New event location (optional)
    
    Returns:
        Success message or error message
    """
    try:
        service = get_calendar_service()
        
        # Get the existing event
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update fields if provided
        if summary is not None:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location
        if start_datetime is not None:
            event['start'] = {'dateTime': start_datetime, 'timeZone': 'UTC'}
        if end_datetime is not None:
            event['end'] = {'dateTime': end_datetime, 'timeZone': 'UTC'}
        
        # Update the event
        updated_event = service.events().update(
            calendarId='primary', 
            eventId=event_id, 
            body=event
        ).execute()
        
        return f"Event updated successfully! Event: {updated_event.get('summary', 'No title')}"
        
    except HttpError as error:
        if error.resp.status == 404:
            return f"Event with ID {event_id} not found."
        return f"Error updating event: {error}"
    except Exception as error:
        return f"Unexpected error updating event: {error}"


@tool(args_schema=DeleteEventInput)
def delete_event_tool(event_id: str) -> str:
    """
    Delete a calendar event.
    
    Args:
        event_id: ID of the event to delete
    
    Returns:
        Success message or error message
    """
    try:
        service = get_calendar_service()
        
        # Get event details before deletion for confirmation
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        event_title = event.get('summary', 'No title')
        
        # Delete the event
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        
        return f"Event '{event_title}' (ID: {event_id}) has been deleted successfully."
        
    except HttpError as error:
        if error.resp.status == 404:
            return f"Event with ID {event_id} not found."
        return f"Error deleting event: {error}"
    except Exception as error:
        return f"Unexpected error deleting event: {error}"


# Additional utility tool for postponing events
@tool(args_schema=PostponeEventInput)
def postpone_event_tool(event_id: str, hours_to_postpone: int) -> str:
    """
    Postpone a calendar event by the specified number of hours.
    
    Args:
        event_id: ID of the event to postpone
        hours_to_postpone: Number of hours to postpone the event
    
    Returns:
        Success message or error message
    """
    try:
        service = get_calendar_service()
        
        # Get the existing event
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Parse current start and end times
        start_dt = datetime.datetime.fromisoformat(
            event['start']['dateTime'].replace('Z', '+00:00')
        )
        end_dt = datetime.datetime.fromisoformat(
            event['end']['dateTime'].replace('Z', '+00:00')
        )
        
        # Add the postponement hours
        new_start = start_dt + datetime.timedelta(hours=hours_to_postpone)
        new_end = end_dt + datetime.timedelta(hours=hours_to_postpone)
        
        # Update the event with new times
        event['start']['dateTime'] = new_start.isoformat()
        event['end']['dateTime'] = new_end.isoformat()
        
        # Update the event
        updated_event = service.events().update(
            calendarId='primary', 
            eventId=event_id, 
            body=event
        ).execute()
        
        event_title = updated_event.get('summary', 'No title')
        return f"Event '{event_title}' has been postponed by {hours_to_postpone} hours. New start time: {new_start.strftime('%Y-%m-%d %H:%M:%S')}"
        
    except HttpError as error:
        if error.resp.status == 404:
            return f"Event with ID {event_id} not found."
        return f"Error postponing event: {error}"
    except Exception as error:
        return f"Unexpected error postponing event: {error}"


# Export all tools as a list for easy use
calendar_tools = [
    create_event_tool,
    list_events_tool,
    update_event_tool,
    delete_event_tool,
    postpone_event_tool
]